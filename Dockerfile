# Dois alvos a partir da mesma base, para a versão do Python e as dependências do
# app ficarem declaradas num lugar só:
#
#   test   docker build --target test .   roda a suíte; não vai para produção
#   prod   docker build .                 o padrão, e o que o compose usa
#
# A versão do Python é parâmetro do build: --build-arg PYTHON_VERSION=3.8 roda
# a mesma suíte no piso que o install.sh aceita.
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FILESWIFT_DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS test

COPY requirements.dev.txt .
RUN pip install --no-cache-dir -r requirements.dev.txt

COPY . .
CMD ["pytest"]

FROM base AS prod

LABEL org.opencontainers.image.title="FileSwift" \
      org.opencontainers.image.description="Servidor de arquivos para rede local" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/brunomint/fileswift"

COPY . .
RUN mkdir -p /data

EXPOSE 5678

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5678')" || exit 1

CMD ["python", "main.py", "--console"]