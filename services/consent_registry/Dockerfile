FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY services/_generated /app/services/_generated
COPY services/consent_registry/app /app/app

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install --no-cache-dir -r /app/app/requirements.txt; fi && \
    chown -R app:app /app

ENV PYTHONPATH=/app

USER app

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=2); print('ok')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
