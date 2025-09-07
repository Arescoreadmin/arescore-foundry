FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true && \
    pip install --no-cache-dir fastapi uvicorn
COPY cron.py /app/cron.py
COPY app.py  /app/app.py
EXPOSE 9102
CMD ["/bin/sh","-lc","python /app/cron.py & exec uvicorn app:app --host 0.0.0.0 --port 9102"]