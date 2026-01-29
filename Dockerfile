# Overleaf-Pull: pull an Overleaf project (zip) into a directory.
# uv for fast, minimal Python deps. Entrypoint = the pull script.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY overleaf_pull.py .
ENTRYPOINT ["python3", "/app/overleaf_pull.py"]
