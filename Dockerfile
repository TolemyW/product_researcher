FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

# No external dependencies; keep editable for quick iteration
RUN pip install --no-cache-dir -e . || true

CMD ["python", "-m", "src.cli", "--help"]
