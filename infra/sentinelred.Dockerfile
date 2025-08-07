FROM python:3.11-slim
WORKDIR /app
COPY backend/sentinelred /app
COPY backend/common /app/common
RUN pip install fastapi uvicorn requests
EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
