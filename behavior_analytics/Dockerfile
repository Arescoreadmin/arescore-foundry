FROM python:3.11.6-slim
WORKDIR /app

COPY behavior_analytics/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY behavior_analytics /app

EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
