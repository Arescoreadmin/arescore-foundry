FROM python:3.12-slim

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY services/_generated /app/services/_generated
COPY services/spawn_service/app /app/app
# Ship the scenario templates into the image so /templates/*.yaml exists
COPY templates /templates

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then \
      pip install --no-cache-dir -r /app/app/requirements.txt; \
    fi && \
    chown -R app:app /app /templates

USER app

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
