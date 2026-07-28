FROM python:3.12-slim

LABEL org.opencontainers.image.title="FileSwift" \
      org.opencontainers.image.description="Servidor de arquivos para rede local" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/brunomint/fileswift"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FILESWIFT_DATA_DIR=/data

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

EXPOSE 5678

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5678')" || exit 1

CMD ["python", "main.py", "--console"]