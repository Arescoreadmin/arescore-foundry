FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY services/revocation_service/app /app/app

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install --no-cache-dir -r /app/app/requirements.txt; fi && \
    chown -R app:app /app

USER app

EXPOSE 8081

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
