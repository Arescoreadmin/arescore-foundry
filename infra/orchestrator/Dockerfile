FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
