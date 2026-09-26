FROM python:3.11-slim AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY services/digital-brain/requirements.txt requirements.txt
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --chown=app:app services/digital-brain/ /app/
COPY --chown=app:app apps/chat-widget/ /apps/chat-widget/
RUN mkdir -p /app/storage/uploads && chown -R app:app /app/storage
USER app
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health',timeout=3)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
