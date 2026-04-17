import re


def clean_markdown(md_text: str) -> str:
    text = md_text or ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 공백 줄 3개 이상 → 2개
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 표 앞뒤 개행 정리
    text = re.sub(r"(\S)\n(\|)", r"\1\n\n\2", text)
    text = re.sub(r"(\|[^\n]*)\n([^\|\n])", r"\1\n\n\2", text)

    # 구분선 앞뒤 개행 정리
    text = re.sub(r"(\S)\n(---)\n", r"\1\n\n\2\n", text)
    text = re.sub(r"\n(---)\n(\S)", r"\n\1\n\n\2", text)

    # 제목 앞뒤 개행 정리
    text = re.sub(r"([^\n])\n(#{1,6}\s)", r"\1\n\n\2", text)
    text = re.sub(r"(#{1,6}\s[^\n]+)\n([^\n#\|])", r"\1\n\n\2", text)

    # 너무 많은 공백 줄 재정리
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def count_stats(md_text: str) -> dict:
    text = md_text or ""
    return {
        "paragraphs": len([line for line in text.splitlines() if line.strip()]),
        "tables": text.count("| ---") + text.lower().count("<table"),
        "images": text.count("!["),
    }