FROM python:3.12-slim

WORKDIR /app

COPY services/_generated /app/services/_generated
COPY services/spawn_service/app /app/app
COPY backend/arescore_foundry_lib /app/arescore_foundry_lib
# Ship the scenario templates into the image so /templates/*.yaml exists
COPY templates /templates

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then \
      pip install -r /app/app/requirements.txt; \
    fi

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
