FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && groupadd --gid 10001 metrics && useradd --uid 10001 --gid 10001 --no-create-home metrics
COPY server/ ./server/
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
ENV METRICS_DB_PATH=/data/metrics.sqlite3 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8093
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8093/healthz", timeout=2)'
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8093", "--no-access-log"]
