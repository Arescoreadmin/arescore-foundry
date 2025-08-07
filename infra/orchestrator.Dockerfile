FROM python:3.11.6-slim
WORKDIR /app

COPY backend/orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/orchestrator /app

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
