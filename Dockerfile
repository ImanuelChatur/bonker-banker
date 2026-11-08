# Bonker Banker web app. Build from the repo root:  docker compose up -d --build
# Needs data/processed/*.parquet in the build folder (gitignored: copy it over or run scripts/precompute.py first).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/requirements-docker.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY backend/ backend/
COPY scripts/ scripts/
COPY data/external/ data/external/
COPY data/processed/ data/processed/
RUN test -f data/processed/monthly_summary.parquet || { \
      echo "data/processed is empty: copy the Parquet files in, or run: python scripts/precompute.py" >&2; exit 1; }

# Run as a normal user. uploads/ holds the login, saved-scenario and statement databases (a volume in compose).
RUN useradd --create-home --uid 1000 app && mkdir -p uploads && chown app:app uploads
USER app

WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# One worker, several threads: login lockouts and sign-up limits are kept in memory, so they must be shared.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", \
     "--timeout", "180", "--access-logfile", "-"]
