FROM python:3.11-slim

WORKDIR /app
COPY services/ot_lab /app
RUN pip install --no-cache-dir fastapi uvicorn[standard]
EXPOSE 8090
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8090"]
