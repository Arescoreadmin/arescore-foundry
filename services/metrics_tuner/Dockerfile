FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cron.py /app/cron.py
CMD ["python","/app/cron.py"]
