# -*- coding: utf-8 -*-
import zipfile
import base64
import io
import re
import logging
import os
from typing import Any, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from lxml import etree

from services.kordoc_service import convert_hwpx_with_kordoc, KordocError
from utils.markdown_postprocess import clean_markdown, count_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hwpx-converter", tags=["HWPX Converter"])

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"


def _tag(ns, name):
    return "{%s}%s" % (ns, name)


# -----------------------------------------
# 기존 Python fallback 파서
# -----------------------------------------

def _parse_char_properties(zf):
    char_map = {}
    try:
        hdr_data = zf.read("Contents/header.xml")
        hdr_root = etree.fromstring(hdr_data)
        char_props = hdr_root.find(".//" + _tag(HH_NS, "charProperties"))
        if char_props is not None:
            for cp in char_props.findall(_tag(HH_NS, "charPr")):
                cp_id = cp.get("id")
                if cp_id is None:
                    continue
                height = int(cp.get("height", "0"))
                has_bold = cp.find(".//" + _tag(HH_NS, "bold")) is not None
                char_map[cp_id] = {"height": height, "bold": has_bold}
    except Exception as e:
        logger.warning("[hwpx-converter] header parse failed: %s", e)
    return char_map


def _extract_paragraph_text(p_elem):
    parts = []
    for run in p_elem.findall(_tag(HP_NS, "run")):
        if run.find(".//" + _tag(HP_NS, "tbl")) is not None:
            continue
        for child in run:
            localname = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""
            if localname == "t" and child.text:
                parts.append(child.text)
            elif localname == "fwSpace":
                count = child.get("count", "1")
                try:
                    parts.append(" " * int(count))
                except ValueError:
                    parts.append(" ")
            elif localname == "tab":
                parts.append("\t")
            elif localname in ("lineBreak", "linesegarray"):
                pass
    return "".join(parts).strip()


def _get_char_pr_id(p_elem):
    for run in p_elem.findall(_tag(HP_NS, "run")):
        if run.find(".//" + _tag(HP_NS, "tbl")) is not None:
            continue
        if run.find(_tag(HP_NS, "t")) is not None:
            return run.get("charPrIDRef")
    return None


def _parse_table_to_md(tbl_elem, char_map, depth=0):
    rows_data = []
    max_cols = 0

    for tr in tbl_elem.findall(_tag(HP_NS, "tr")):
        cells = []
        for tc in tr.findall(_tag(HP_NS, "tc")):
            nested_tbls = tc.findall(".//" + _tag(HP_NS, "tbl"))
            cell_parts = []

            for sl in tc.findall(_tag(HP_NS, "subList")):
                for p in sl.findall(_tag(HP_NS, "p")):
                    in_nested = False
                    ancestor = p.getparent()
                    while ancestor is not None and ancestor is not tc:
                        if etree.QName(ancestor.tag).localname == "tbl":
                            in_nested = True
                            break
                        ancestor = ancestor.getparent()
                    if in_nested:
                        continue
                    text = _extract_paragraph_text(p)
                    if text:
                        cell_parts.append(text)

            if nested_tbls and depth < 2:
                for nt in nested_tbls:
                    nested_md = _parse_table_to_md(nt, char_map, depth + 1)
                    if nested_md:
                        cell_parts.append(nested_md)

            cell_text = " ".join(cell_parts)
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

    filtered_rows = []
    for row in rows_data:
        if any(c.strip() for c in row):
            filtered_rows.append(row)
    if not filtered_rows:
        return ""

    rows_data = filtered_rows
    md_lines = []
    header = rows_data[0]
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in rows_data[1:]:
        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


def _extract_images_from_hwpx(zf):
    images = {}
    img_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"]
    for name in zf.namelist():
        lower = name.lower()
        if ("bindata" in lower or "media" in lower or "preview" not in lower) and any(lower.endswith(ext) for ext in img_extensions):
            if "preview" in lower:
                continue
            try:
                data = zf.read(name)
                b64 = base64.b64encode(data).decode("utf-8")
                if lower.endswith(".png"):
                    mime = "image/png"
                elif lower.endswith((".jpg", ".jpeg")):
                    mime = "image/jpeg"
                elif lower.endswith(".gif"):
                    mime = "image/gif"
                else:
                    mime = "image/png"
                basename = os.path.basename(name)
                key = os.path.splitext(basename)[0]
                images[key] = (mime, b64)
                images[name] = (mime, b64)
                images[basename] = (mime, b64)
            except Exception as e:
                logger.warning("[hwpx-converter] image extract failed: %s - %s", name, e)
    return images


def _find_image_ref(p_elem):
    for child in p_elem.iter():
        localname = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""
        if localname in ("img", "picture", "pic", "shapeObject"):
            bin_id = child.get("binDataId") or child.get("binaryItemId")
            if bin_id:
                return bin_id
        if localname == "binDataId" and child.text:
            return child.text
        if localname in ("imgData", "binItem", "image"):
            href = child.get("href") or child.get("src") or child.get("binDataId")
            if href:
                return href
    return None


def _find_section_files(zf):
    section_files = []
    for name in zf.namelist():
        lower = name.lower()
        if "section" in lower and lower.endswith(".xml"):
            section_files.append(name)
    if not section_files:
        for name in zf.namelist():
            lower = name.lower()
            if lower.startswith("contents/") and lower.endswith(".xml") and "header" not in lower and "settings" not in lower:
                try:
                    content = zf.read(name)
                    if b"<hp:" in content or b"<hs:" in content:
                        section_files.append(name)
                except Exception:
                    pass
    section_files.sort()
    return section_files


def _convert_section(section_xml, char_map, images, image_mode, image_counter):
    try:
        root = etree.fromstring(section_xml)
    except etree.XMLSyntaxError as e:
        logger.warning("[hwpx-converter] XML parse error: %s", e)
        return []

    md_lines = []

    for p_elem in root.findall(_tag(HP_NS, "p")):
        tbl = None
        for run in p_elem.findall(_tag(HP_NS, "run")):
            t = run.find(_tag(HP_NS, "tbl"))
            if t is not None:
                tbl = t
                break

        if tbl is not None:
            pre_text = _extract_paragraph_text(p_elem)
            if pre_text:
                md_lines.append(pre_text)
                md_lines.append("")

            table_md = _parse_table_to_md(tbl, char_map, depth=0)
            if table_md:
                md_lines.append("")
                md_lines.append(table_md)
                md_lines.append("")
        else:
            img_ref = _find_image_ref(p_elem)
            if img_ref and images:
                image_counter[0] += 1
                img_num = image_counter[0]
                img_data = None
                for kc in [img_ref, "image" + img_ref, "IMG" + img_ref]:
                    if kc in images:
                        img_data = images[kc]
                        break
                if not img_data:
                    for ik, iv in images.items():
                        if img_ref in ik or ik in img_ref:
                            img_data = iv
                            break
                if img_data:
                    mime, b64 = img_data
                    if image_mode == "inline":
                        md_lines.append("")
                        md_lines.append("![image " + str(img_num) + "](data:" + mime + ";base64," + b64 + ")")
                        md_lines.append("")

            text = _extract_paragraph_text(p_elem)
            if not text:
                if md_lines and md_lines[-1] != "":
                    md_lines.append("")
                continue

            char_id = _get_char_pr_id(p_elem)
            is_title = False
            if char_id and char_id in char_map:
                info = char_map[char_id]
                if info["height"] >= 1400 and info["bold"]:
                    md_lines.append("")
                    md_lines.append("## " + text)
                    md_lines.append("")
                    is_title = True
                elif info["height"] >= 1400:
                    md_lines.append("")
                    md_lines.append("## " + text)
                    md_lines.append("")
                    is_title = True
                elif info["height"] >= 1200 and info["bold"]:
                    md_lines.append("")
                    md_lines.append("### " + text)
                    md_lines.append("")
                    is_title = True

            if not is_title:
                md_lines.append(text)

    return md_lines


def _clean_markdown_fallback(md_text):
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

    char_map = _parse_char_properties(zf)
    images = _extract_images_from_hwpx(zf)
    section_files = _find_section_files(zf)
    if not section_files:
        raise ValueError("No content sections found in HWPX file.")

    all_md_lines = []
    image_counter = [0]
    table_count = 0

    for sf in section_files:
        try:
            section_xml = zf.read(sf)
            lines = _convert_section(section_xml, char_map, images, image_mode, image_counter)
            if lines:
                section_text = "\n".join(lines)
                table_count += section_text.count("| ---")
                all_md_lines.append(section_text)
        except Exception as e:
            logger.warning("[hwpx-converter] section failed: %s - %s", sf, e)

    if len(all_md_lines) > 1:
        full_md = "\n\n---\n\n".join(all_md_lines)
    else:
        full_md = "\n".join(all_md_lines)

    full_md = _clean_markdown_fallback(full_md)

    extracted_images = []
    if image_mode == "separate":
        seen = set()
        for _, (mime, b64) in images.items():
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


def _run_best_effort_conversion(file_bytes: bytes, filename: str, image_mode: str) -> Dict[str, Any]:
    errors = []

    try:
        kordoc_result = convert_hwpx_with_kordoc(
            file_bytes=file_bytes,
            filename=filename,
            image_mode=image_mode,
            timeout_sec=120,
        )
        markdown = clean_markdown(kordoc_result["markdown"])
        stats = count_stats(markdown)

        return {
            "markdown": markdown,
            "images": kordoc_result.get("images", []),
            "stats": stats,
            "engine": "kordoc",
            "fallback_used": False,
            "errors": [],
        }
    except KordocError as e:
        logger.warning("[hwpx-converter] kordoc failed, fallback start: %s", e)
        errors.append("kordoc: " + str(e))
    except Exception as e:
        logger.warning("[hwpx-converter] unexpected kordoc error, fallback start: %s", e)
        errors.append("kordoc: " + str(e))

    try:
        fallback_result = convert_hwpx_to_markdown(
            file_bytes=file_bytes,
            image_mode=image_mode,
            filename=filename,
        )
        markdown = clean_markdown(fallback_result["markdown"])
        stats = count_stats(markdown)

        return {
            "markdown": markdown,
            "images": fallback_result.get("images", []),
            "stats": stats,
            "engine": "python_fallback",
            "fallback_used": True,
            "errors": errors,
        }
    except Exception as e:
        logger.error("[hwpx-converter] fallback also failed: %s", e, exc_info=True)
        errors.append("python_fallback: " + str(e))
        raise HTTPException(status_code=500, detail=" / ".join(errors))


# -----------------------------------------
# API Endpoints
# -----------------------------------------

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

    if image_mode not in ("inline", "separate"):
        raise HTTPException(status_code=400, detail="image_mode must be 'inline' or 'separate'.")

    result = _run_best_effort_conversion(file_bytes, file.filename, image_mode)

    return JSONResponse({
        "success": True,
        "filename": file.filename,
        "markdown": result["markdown"],
        "images": result["images"] if image_mode == "separate" else [],
        "stats": result["stats"],
        "engine": result["engine"],
        "fallback_used": result["fallback_used"],
        "errors": result["errors"],
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

    if image_mode not in ("inline", "separate"):
        raise HTTPException(status_code=400, detail="image_mode must be 'inline' or 'separate'.")

    result = _run_best_effort_conversion(file_bytes, file.filename, image_mode)

    md_filename = os.path.splitext(file.filename)[0] + ".md"
    md_bytes = result["markdown"].encode("utf-8")

    headers = {
        "Content-Disposition": f'attachment; filename="{md_filename}"',
        "X-Stats-Paragraphs": str(result["stats"]["paragraphs"]),
        "X-Stats-Tables": str(result["stats"]["tables"]),
        "X-Stats-Images": str(result["stats"]["images"]),
        "X-Engine": result["engine"],
        "X-Fallback-Used": str(result["fallback_used"]).lower(),
    }

    return StreamingResponse(
        io.BytesIO(md_bytes),
        media_type="text/markdown; charset=utf-8",
        headers=headers,
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
        "engines": ["kordoc", "python_fallback"],
    }