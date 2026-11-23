# Free, local-first runtime. The image contains code only; data and secrets are mounted.
FROM python:3.12.14-slim-bookworm AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /uvx /bin/
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin himaroad

WORKDIR /app
COPY --chown=himaroad:himaroad . /app
RUN uv sync --locked --no-dev --no-editable \
    && mkdir -p /data /home/himaroad/.cache \
    && chown -R himaroad:himaroad /data /home/himaroad /app

USER himaroad
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MPLCONFIGDIR=/data/cache/matplotlib \
    HIMAROAD_DATA_DIR=/data \
    DATA_ROOT=/data/copilot \
    REPORT_FONT=/data/copilot/cache/fonts/NotoSansDevanagari.ttf \
    HIMAROAD_RUNTIME=local

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=4)" || exit 1

CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "64", "--timeout-keep-alive", "5"]
