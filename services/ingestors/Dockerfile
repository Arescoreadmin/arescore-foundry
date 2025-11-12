FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/_generated /app/services/_generated
COPY services/ingestors/app /app/app
COPY backend/arescore_foundry_lib /app/arescore_foundry_lib

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    python -m pip install --upgrade pip && \
    pip install -r /app/app/requirements.txt

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
