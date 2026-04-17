import os
import re
import json
import shutil
import base64
import tempfile
import logging
import subprocess
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class KordocError(Exception):
    pass


def _which_kordoc() -> str:
    candidates = ["kordoc"]
    for cmd in candidates:
        found = shutil.which(cmd)
        if found:
            return found
    raise KordocError("kordoc CLI를 찾을 수 없습니다. Dockerfile에서 kordoc 설치 여부를 확인하세요.")


def _read_text_file(path: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            continue
    raise KordocError(f"Markdown 결과 파일을 읽을 수 없습니다: {path}")


def _guess_mime_by_ext(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".bmp"):
        return "image/bmp"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    return "application/octet-stream"


def _extract_local_image_paths(markdown: str) -> List[str]:
    pattern = r'!\[[^\]]*\]\(([^)]+)\)'
    paths = re.findall(pattern, markdown or "")
    result = []
    for p in paths:
        if p.startswith("data:"):
            continue
        if p.startswith("http://") or p.startswith("https://"):
            continue
        result.append(p)
    return result


def _replace_image_paths_with_data_uri(markdown: str, base_dir: str) -> str:
    def replacer(match):
        alt = match.group(1)
        src = match.group(2)

        if src.startswith("data:") or src.startswith("http://") or src.startswith("https://"):
            return match.group(0)

        img_path = os.path.normpath(os.path.join(base_dir, src))
        if not os.path.exists(img_path):
            return match.group(0)

        try:
            with open(img_path, "rb") as f:
                raw = f.read()
            mime = _guess_mime_by_ext(img_path)
            b64 = base64.b64encode(raw).decode("utf-8")
            return f"![{alt}](data:{mime};base64,{b64})"
        except Exception as e:
            logger.warning("[kordoc-service] inline image convert failed: %s", e)
            return match.group(0)

    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replacer, markdown or "")


def _collect_separate_images(markdown: str, base_dir: str) -> List[Dict[str, str]]:
    images = []
    seen = set()

    for rel_path in _extract_local_image_paths(markdown):
        abs_path = os.path.normpath(os.path.join(base_dir, rel_path))
        if not os.path.exists(abs_path):
            continue

        try:
            with open(abs_path, "rb") as f:
                raw = f.read()
            b64 = base64.b64encode(raw).decode("utf-8")
            if b64 in seen:
                continue
            seen.add(b64)
            images.append({
                "name": os.path.basename(abs_path),
                "mime": _guess_mime_by_ext(abs_path),
                "data": b64,
            })
        except Exception as e:
            logger.warning("[kordoc-service] separate image collect failed: %s", e)

    return images


def convert_hwpx_with_kordoc(file_bytes: bytes, filename: str, image_mode: str = "inline", timeout_sec: int = 120) -> Dict[str, Any]:
    if not filename.lower().endswith(".hwpx"):
        raise KordocError("Only .hwpx files are supported.")

    kordoc_cmd = _which_kordoc()

    with tempfile.TemporaryDirectory(prefix="hwpx_kordoc_") as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        output_path = os.path.join(tmpdir, "output.md")

        with open(input_path, "wb") as f:
            f.write(file_bytes)

        cmd = [kordoc_cmd, input_path, "-o", output_path]

        logger.info("[kordoc-service] run: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise KordocError(f"kordoc 실행 시간이 {timeout_sec}초를 초과했습니다.")

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            logger.error("[kordoc-service] failed stdout=%s stderr=%s", stdout, stderr)
            raise KordocError(stderr or stdout or "kordoc 변환 실패")

        if not os.path.exists(output_path):
            logger.error("[kordoc-service] output.md not found stdout=%s stderr=%s", stdout, stderr)
            raise KordocError("kordoc 변환 결과 파일(output.md)을 찾을 수 없습니다.")

        markdown = _read_text_file(output_path)

        if image_mode == "inline":
            markdown = _replace_image_paths_with_data_uri(markdown, tmpdir)
            images = []
        else:
            images = _collect_separate_images(markdown, tmpdir)

        stats = {
            "paragraphs": len([line for line in markdown.splitlines() if line.strip()]),
            "tables": markdown.count("| ---") + markdown.lower().count("<table"),
            "images": markdown.count("!["),
        }

        return {
            "markdown": markdown,
            "images": images,
            "stats": stats,
            "engine": "kordoc",
            "debug": {
                "stdout": stdout,
                "stderr": stderr,
            },
        }