# ─────────────────────────────────────────────────────────────────────────────
# Aegis-APAC  container — works on Render, HF Spaces, Cloud Run
# PORT env var is injected by Render; falls back to 7860 for HF Spaces
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Aegis-APAC"
LABEL org.opencontainers.image.description="Anticipatory Cyclone Impact Platform for Coastal APAC"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEMO_MODE=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY src/        src/
COPY contracts/  contracts/
COPY regions/    regions/
COPY data/golden/ data/golden/
COPY web/        web/
COPY DECISIONS.md AGENTS.md ./

RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-7860}/health || exit 1

EXPOSE 7860 10000

CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-7860}
