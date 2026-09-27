# -----------------------------------------------------------------------------
# Aegis-APAC  ·  Hugging Face Spaces container
# HF Spaces runs as UID 1000 on port 7860 — both required.
# -----------------------------------------------------------------------------
FROM python:3.11-slim

# Metadata expected by HF Spaces
LABEL org.opencontainers.image.title="Aegis-APAC"
LABEL org.opencontainers.image.description="Anticipatory Cyclone Impact Platform for Coastal APAC"

# Prevent .pyc spam and force unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEMO_MODE=true \
    PORT=7860

WORKDIR /app

# -- System deps ---------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# -- Python deps ---------------------------------------------------------------
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# -- Application code ----------------------------------------------------------
COPY src/        src/
COPY contracts/  contracts/
COPY regions/    regions/
COPY data/golden/ data/golden/
COPY web/        web/
COPY DECISIONS.md AGENTS.md ./

# -- HF Spaces: non-root user UID=1000 ----------------------------------------
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# -- Health check --------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:7860/health || exit 1

EXPOSE 7860

# -- Start ---------------------------------------------------------------------
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
