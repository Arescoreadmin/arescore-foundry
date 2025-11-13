FROM python:3.11-slim

WORKDIR /app
COPY services/network_overlay /app

RUN pip install --no-cache-dir fastapi uvicorn[standard]

EXPOSE 8087

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8087"]
