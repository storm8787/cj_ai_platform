# Azure Container Apps 배포용 Dockerfile
FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

ENV HF_HOME=/app/.cache/huggingface
ENV HF_HUB_CACHE=/app/.cache/huggingface/hub
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers
ENV EMBEDDING_MODEL=/app/models/bge-m3
ENV PYTHONUNBUFFERED=1

# 의존성 먼저 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

RUN mkdir -p /app/models && \
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-m3', local_dir='/app/models/bge-m3', local_dir_use_symlinks=False)" && \
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='jhgan/ko-sroberta-multitask', local_dir='/app/models/ko-sroberta-multitask', local_dir_use_symlinks=False)"

# 애플리케이션 코드 복사 (vectorstore 파일 포함)
COPY . .

# 벡터스토어 디렉토리가 제대로 복사되었는지 확인
RUN echo "Checking vectorstore files..." && \
    ls -lah /app/data/vectorstores/ || echo "Vectorstore directory not found"

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Force rebuild: 2026-01-22-v1