FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
