FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
USER appuser
EXPOSE 9000
HEALTHCHECK --interval=20s --timeout=3s --retries=3 CMD curl -fsS http://localhost:9000/ready || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
