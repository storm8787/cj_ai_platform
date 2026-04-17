# -*- coding: utf-8 -*-
import zipfile
import base64
import io
import re
import logging
import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from lxml import etree

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hwpx-converter", tags=["HWPX Converter"])

HWPX_NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp6": "http://www.hancom.co.kr/hwpml/2011/paragraph6",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hr": "http://www.hancom.co.kr/hwpml/2011/run",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}

OUTLINE_LEVEL_MAP = {
    "0": "#",
    "1": "##",
    "2": "###",
    "3": "####",
    "4": "#####",
    "5": "######",
}


def _extract_text_from_run(run_elem, ns):
    texts = []
    for t in run_elem.iter():
        tag = etree.QName(t.tag).localname if isinstance(t.tag, str) else ""
        if tag == "t" and t.text:
            texts.append(t.text)
        elif tag == "fwSpace":
            count = t.get("count", "1")
            try:
                texts.append(" " * int(count))
            except ValueError:
                texts.append(" ")
        elif tag == "tab":
            texts.append("\t")
        elif tag == "lineBreak" or tag == "linesegarray":
            texts.append("\n")
    return "".join(texts)


def _get_outline_level(para_elem, ns):
    for attr_name in ["outlineLevel", "outlineLvl"]:
        val = para_elem.get(attr_name)
        if val and val != "none":
            return val
    return None


def _detect_bold(run_elem, ns):
    for child in run_elem.iter():
        tag = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""
        if tag == "charPr" or tag == "rPr":
            bold = child.get("bold")
            if bold and bold.lower() in ("true", "1"):
                return True
    return False


def _extract_images_from_hwpx(zf):
    images = {}
    img_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".wmf", ".emf"]
    for name in zf.namelist():
        lower = name.lower()
        if ("bindata" in lower or "media" in lower) and any(lower.endswith(ext) for ext in img_extensions):
            try:
                data = zf.read(name)
                b64 = base64.b64encode(data).decode("utf-8")
                if lower.endswith(".png"):
                    mime = "image/png"
                elif lower.endswith((".jpg", ".jpeg")):
                    mime = "image/jpeg"
                elif lower.endswith(".gif"):
                    mime = "image/gif"
                elif lower.endswith(".bmp"):
                    mime = "image/bmp"
                else:
                    mime = "image/png"
                basename = os.path.basename(name)
                key = os.path.splitext(basename)[0]
                images[key] = (mime, b64)
                images[name] = (mime, b64)
                images[basename] = (mime, b64)
                logger.info("[hwpx-converter] image extracted: %s (%d bytes)", name, len(data))
            except Exception as e:
                logger.warning("[hwpx-converter] image extract failed: %s - %s", name, e)
    return images


def _find_image_ref(para_elem, ns):
    for child in para_elem.iter():
        tag = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""
        if tag in ("img", "picture", "drawText", "shapeObject", "pic"):
            bin_id = child.get("binDataId") or child.get("binaryItemId")
            if bin_id:
                return bin_id
        if tag == "binDataId" and child.text:
            return child.text
        if tag in ("imgData", "binItem", "image"):
            href = child.get("href") or child.get("src") or child.get("binDataId")
            if href:
                return href
    return None


def _parse_table(tbl_elem, ns):
    rows_data = []
    max_cols = 0
    for row in tbl_elem.iter():
        tag = etree.QName(row.tag).localname if isinstance(row.tag, str) else ""
        if tag != "tr":
            continue
        cells = []
        for cell in row.iter():
            cell_tag = etree.QName(cell.tag).localname if isinstance(cell.tag, str) else ""
            if cell_tag != "tc":
                continue
            cell_texts = []
            for t_elem in cell.iter():
                t_tag = etree.QName(t_elem.tag).localname if isinstance(t_elem.tag, str) else ""
                if t_tag == "t" and t_elem.text:
                    cell_texts.append(t_elem.text.strip())
                elif t_tag == "fwSpace":
                    cell_texts.append(" ")
            cell_text = " ".join(cell_texts).strip()
            cell_text = cell_text.replace("\n", " ").replace("\r", "")
            cell_text = cell_text.replace("|", "\\|")
            cells.append(cell_text if cell_text else " ")
        if cells:
            rows_data.append(cells)
            max_cols = max(max_cols, len(cells))
    if not rows_data or max_cols == 0:
        return ""
    for row in rows_data:
        while len(row) < max_cols:
            row.append(" ")
    md_lines = []
    header = rows_data[0]
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in rows_data[1:]:
        md_lines.append("| " + " | ".join(row) + " |")
    return "\n".join(md_lines)


def _find_section_files(zf):
    section_files = []
    for name in zf.namelist():
        lower = name.lower()
        if ("section" in lower or "content" in lower) and lower.endswith(".xml"):
            section_files.append(name)
    section_files.sort()
    return section_files


def _convert_section_to_markdown(section_xml, images, image_mode, image_counter):
    try:
        root = etree.fromstring(section_xml)
    except etree.XMLSyntaxError as e:
        logger.warning("[hwpx-converter] XML parse error: %s", e)
        return ""
    md_parts = []
    for elem in root.iter():
        tag = etree.QName(elem.tag).localname if isinstance(elem.tag, str) else ""
        if tag == "tbl":
            table_md = _parse_table(elem, HWPX_NS)
            if table_md:
                md_parts.append("")
                md_parts.append(table_md)
                md_parts.append("")
            continue
        if tag not in ("p", "para", "paragraph"):
            continue
        parent = elem.getparent()
        if parent is not None:
            parent_tag = etree.QName(parent.tag).localname if isinstance(parent.tag, str) else ""
            if parent_tag in ("tc", "cell", "tableCell"):
                continue
            grandparent = parent.getparent()
            if grandparent is not None:
                gp_tag = etree.QName(grandparent.tag).localname if isinstance(grandparent.tag, str) else ""
                if gp_tag in ("tc", "cell", "tableCell"):
                    continue
        img_ref = _find_image_ref(elem, HWPX_NS)
        if img_ref and images:
            image_counter[0] += 1
            img_num = image_counter[0]
            img_data = None
            for key_candidate in [img_ref, "image" + img_ref, "IMG" + img_ref]:
                if key_candidate in images:
                    img_data = images[key_candidate]
                    break
            if not img_data:
                for img_key, img_val in images.items():
                    if img_ref in img_key or img_key in img_ref:
                        img_data = img_val
                        break
            if img_data:
                mime, b64 = img_data
                if image_mode == "inline":
                    md_parts.append("")
                    md_parts.append("![image " + str(img_num) + "](data:" + mime + ";base64," + b64 + ")")
                    md_parts.append("")
                else:
                    ext = mime.split("/")[-1]
                    md_parts.append("")
                    md_parts.append("![image " + str(img_num) + "](images/image_" + str(img_num) + "." + ext + ")")
                    md_parts.append("")
        para_text = _extract_text_from_run(elem, HWPX_NS)
        para_text = para_text.strip()
        if not para_text:
            if md_parts and md_parts[-1] != "":
                md_parts.append("")
            continue
        outline_level = _get_outline_level(elem, HWPX_NS)
        if outline_level and outline_level in OUTLINE_LEVEL_MAP:
            heading_prefix = OUTLINE_LEVEL_MAP[outline_level]
            md_parts.append("")
            md_parts.append(heading_prefix + " " + para_text)
            md_parts.append("")
        else:
            is_all_bold = False
            runs = list(elem.iter())
            if runs and len(para_text) < 100:
                bold_count = sum(1 for r in runs if _detect_bold(r, HWPX_NS))
                if bold_count > 0 and len(para_text) < 50:
                    is_all_bold = True
            if is_all_bold:
                md_parts.append("")
                md_parts.append("**" + para_text + "**")
                md_parts.append("")
            else:
                md_parts.append(para_text)
    return "\n".join(md_parts)


def _clean_markdown(md_text):
    lines = md_text.split("\n")
    cleaned = []
    prev_empty = False
    for line in lines:
        is_empty = line.strip() == ""
        if is_empty and prev_empty:
            continue
        cleaned.append(line)
        prev_empty = is_empty
    result = "\n".join(cleaned).strip()
    result = re.sub(r"(\S)\n(\|)", r"\1\n\n\2", result)
    result = re.sub(r"(\|[^\n]*)\n(\S)", r"\1\n\n\2", result)
    return result


def convert_hwpx_to_markdown(file_bytes, image_mode="inline", filename="document"):
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes), "r")
    except zipfile.BadZipFile:
        raise ValueError("Not a valid HWPX file.")
    images = _extract_images_from_hwpx(zf)
    section_files = _find_section_files(zf)
    if not section_files:
        for name in zf.namelist():
            if name.lower().endswith(".xml") and "header" not in name.lower() and "settings" not in name.lower():
                try:
                    content = zf.read(name)
                    if b"<hp:" in content or b"<p " in content or b"<para" in content:
                        section_files.append(name)
                except Exception:
                    pass
        section_files.sort()
    if not section_files:
        raise ValueError("No content sections found in HWPX file.")
    all_md_parts = []
    image_counter = [0]
    table_count = 0
    for sf in section_files:
        try:
            section_xml = zf.read(sf)
            section_md = _convert_section_to_markdown(section_xml, images, image_mode, image_counter)
            if section_md.strip():
                all_md_parts.append(section_md)
                table_count += section_md.count("| ---")
        except Exception as e:
            logger.warning("[hwpx-converter] section convert failed: %s - %s", sf, e)
    if len(all_md_parts) > 1:
        full_md = "\n\n---\n\n".join(all_md_parts)
    else:
        full_md = "\n".join(all_md_parts)
    full_md = _clean_markdown(full_md)
    extracted_images = []
    if image_mode == "separate":
        seen = set()
        for key, (mime, b64) in images.items():
            if b64 not in seen:
                seen.add(b64)
                ext = mime.split("/")[-1]
                extracted_images.append({
                    "name": "image_" + str(len(extracted_images) + 1) + "." + ext,
                    "mime": mime,
                    "data": b64,
                })
    zf.close()
    return {
        "markdown": full_md,
        "images": extracted_images,
        "stats": {
            "paragraphs": len([l for l in full_md.split("\n") if l.strip()]),
            "tables": table_count,
            "images": image_counter[0],
        }
    }


@router.post("/convert")
async def convert_hwpx(
    file: UploadFile = File(...),
    image_mode: str = Form("inline"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    if not file.filename.lower().endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are supported.")
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail="File read error: " + str(e))
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit.")
    try:
        result = convert_hwpx_to_markdown(file_bytes=file_bytes, image_mode=image_mode, filename=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("[hwpx-converter] convert error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Conversion error: " + str(e))
    return JSONResponse({
        "success": True,
        "filename": file.filename,
        "markdown": result["markdown"],
        "images": result["images"] if image_mode == "separate" else [],
        "stats": result["stats"],
    })


@router.post("/convert-download")
async def convert_hwpx_download(
    file: UploadFile = File(...),
    image_mode: str = Form("inline"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    if not file.filename.lower().endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="Only .hwpx files are supported.")
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail="File read error: " + str(e))
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit.")
    try:
        result = convert_hwpx_to_markdown(file_bytes=file_bytes, image_mode=image_mode, filename=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("[hwpx-converter] convert error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Conversion error: " + str(e))
    md_filename = os.path.splitext(file.filename)[0] + ".md"
    md_bytes = result["markdown"].encode("utf-8")
    return StreamingResponse(
        io.BytesIO(md_bytes),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=" + md_filename,
            "X-Stats-Paragraphs": str(result["stats"]["paragraphs"]),
            "X-Stats-Tables": str(result["stats"]["tables"]),
            "X-Stats-Images": str(result["stats"]["images"]),
        }
    )


@router.get("/status")
async def get_status():
    return {
        "status": "healthy",
        "feature": "hwpx_converter",
        "supported_formats": ["hwpx"],
        "output_format": "markdown",
        "image_modes": ["inline", "separate"],
        "max_file_size_mb": 50,
    }