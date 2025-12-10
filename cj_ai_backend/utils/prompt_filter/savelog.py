import csv
import os
from datetime import datetime
from pathlib import Path

# 로그 디렉토리 설정
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "prompt_filter_log.csv"

def save_log(text: str, is_malicious: bool, reason: str):
    """
    필터링 결과를 CSV 로그로 저장
    :param text: 사용자 입력 원문
    :param is_malicious: 위험 여부 (True/False)
    :param reason: 탐지 사유 또는 일치한 패턴
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, text, is_malicious, reason]

    file_exists = LOG_FILE.is_file()

    with open(LOG_FILE, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "text", "is_malicious", "reason"])
        writer.writerow(row)