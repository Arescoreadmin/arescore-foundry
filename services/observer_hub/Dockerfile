FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn
COPY app.py /app/app.py
EXPOSE 9092
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","9092"]