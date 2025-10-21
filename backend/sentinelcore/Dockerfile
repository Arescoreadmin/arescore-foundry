# backend/sentinelcore/Dockerfile (or wherever it lives)
FROM python:3.11-slim
RUN useradd -m appuser
WORKDIR /app
COPY backend/sentinelcore/app/ /app/app/
COPY backend/sentinelcore/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/app
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
