
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt
COPY indexer.py .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD ["python","-c","import urllib.request as u; u.urlopen(\"http://127.0.0.1:8080/health\", timeout=2).read(); print(\"ok\")"]
CMD ["python","indexer.py"]
