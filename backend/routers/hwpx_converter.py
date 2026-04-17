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

HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"


def _tag(ns, name):
    return "{%s}%s" % (ns, name)


# -----------------------------------------
# Header parsing (font size / bold info)
# -----------------------------------------

def _parse_char_properties(zf):
    """Parse header.xml to build charPrIDRef -> {height, bold} map"""
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


# -----------------------------------------
# Text extraction from a single <p> element
# -----------------------------------------

def _extract_paragraph_text(p_elem):
    """Extract text from <hp:p>, handling <hp:t>, fwSpace, tab, lineBreak.
    Only collects text from <hp:run> children, NOT from nested tables."""
    parts = []
    for run in p_elem.findall(_tag(HP_NS, "run")):
        # Skip runs that contain tables
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
                pass  # ignore line segments
    return "".join(parts).strip()


def _get_char_pr_id(p_elem):
    """Get the charPrIDRef of the first text-bearing run"""
    for run in p_elem.findall(_tag(HP_NS, "run")):
        if run.find(".//" + _tag(HP_NS, "tbl")) is not None:
            continue
        if run.find(_tag(HP_NS, "t")) is not None:
            return run.get("charPrIDRef")
    return None


# -----------------------------------------
# Table parsing
# -----------------------------------------

def _parse_table_to_md(tbl_elem, char_map, depth=0):
    """Convert <hp:tbl> to Markdown table string.
    Handles nested tables by recursively converting them inline."""
    rows_data = []
    max_cols = 0

    for tr in tbl_elem.findall(_tag(HP_NS, "tr")):
        cells = []
        for tc in tr.findall(_tag(HP_NS, "tc")):
            # Check for nested tables inside this cell
            nested_tbls = tc.findall(".//" + _tag(HP_NS, "tbl"))

            cell_parts = []
            # Collect direct text from subList > p (not inside nested tables)
            for sl in tc.findall(_tag(HP_NS, "subList")):
                for p in sl.findall(_tag(HP_NS, "p")):
                    # Check if this p is inside a nested tbl
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

            # If cell has nested tables, convert them and append
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

    # Pad rows to same column count
    for row in rows_data:
        while len(row) < max_cols:
            row.append(" ")

    # Remove completely empty rows
    filtered_rows = []
    for row in rows_data:
        if any(c.strip() for c in row):
            filtered_rows.append(row)
    if not filtered_rows:
        return ""
    rows_data = filtered_rows

    # Build markdown table
    md_lines = []
    header = rows_data[0]
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in rows_data[1:]:
        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


# -----------------------------------------
# Image extraction
# -----------------------------------------

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
    """Find image reference in paragraph"""
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


# -----------------------------------------
# Section conversion
# -----------------------------------------

def _find_section_files(zf):
    section_files = []
    for name in zf.namelist():
        lower = name.lower()
        if "section" in lower and lower.endswith(".xml"):
            section_files.append(name)
    if not section_files:
        # Fallback: look for content XML files
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
    """Convert one section XML to markdown lines"""
    try:
        root = etree.fromstring(section_xml)
    except etree.XMLSyntaxError as e:
        logger.warning("[hwpx-converter] XML parse error: %s", e)
        return []

    md_lines = []

    # Process only top-level <hp:p> elements (direct children of <hs:sec>)
    for p_elem in root.findall(_tag(HP_NS, "p")):

        # Check if this paragraph contains a table
        tbl = None
        for run in p_elem.findall(_tag(HP_NS, "run")):
            t = run.find(_tag(HP_NS, "tbl"))
            if t is not None:
                tbl = t
                break

        if tbl is not None:
            # This paragraph holds a table
            # First output any text before the table (rare but possible)
            pre_text = _extract_paragraph_text(p_elem)
            if pre_text:
                md_lines.append(pre_text)
                md_lines.append("")

            # Convert the table
            table_md = _parse_table_to_md(tbl, char_map, depth=0)
            if table_md:
                md_lines.append("")
                md_lines.append(table_md)
                md_lines.append("")
        else:
            # Regular paragraph (no table)
            # Check for image
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
                    else:
                        ext = mime.split("/")[-1]
                        md_lines.append("")
                        md_lines.append("![image " + str(img_num) + "](images/image_" + str(img_num) + "." + ext + ")")
                        md_lines.append("")

            # Extract text
            text = _extract_paragraph_text(p_elem)
            if not text:
                if md_lines and md_lines[-1] != "":
                    md_lines.append("")
                continue

            # Determine if this is a heading based on font size
            char_id = _get_char_pr_id(p_elem)
            is_title = False
            if char_id and char_id in char_map:
                info = char_map[char_id]
                # height >= 1400 and bold -> heading level 1
                # height >= 1200 and bold -> heading level 2
                # height >= 1400 without bold -> heading level 2
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


# -----------------------------------------
# Post-processing
# -----------------------------------------

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
    # Ensure blank lines around tables
    result = re.sub(r"(\S)\n(\|)", r"\1\n\n\2", result)
    result = re.sub(r"(\|[^\n]*)\n(\S)", r"\1\n\n\2", result)
    return result


# -----------------------------------------
# Main conversion
# -----------------------------------------

def convert_hwpx_to_markdown(file_bytes, image_mode="inline", filename="document"):
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes), "r")
    except zipfile.BadZipFile:
        raise ValueError("Not a valid HWPX file.")

    # Parse header for char properties
    char_map = _parse_char_properties(zf)

    # Extract images
    images = _extract_images_from_hwpx(zf)

    # Find section files
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
    full_md = _clean_markdown(full_md)

    # Separate mode images
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