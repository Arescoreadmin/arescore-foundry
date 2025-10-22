# infra/sentinelcore.Dockerfile (or whatever you use)
WORKDIR /app
COPY backend/sentinelcore/app/ /app/app/
COPY backend/sentinelcore/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
