FROM python:3.11-slim
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system worker && useradd --system --gid worker --home-dir /app worker
WORKDIR /app
COPY services/rpa-worker/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt && \
    python -m playwright install --with-deps chromium && \
    mkdir -p /app/data && chown -R worker:worker /app
COPY --chown=worker:worker services/rpa-worker/ /app/
USER worker
CMD ["python", "worker_main.py"]
