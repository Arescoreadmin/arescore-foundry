FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Orchestrator deps
COPY services/orchestrator/app/requirements.txt /tmp/orchestrator-requirements.txt

# Shared policy/lib deps – NOTE: backend/ path
COPY backend/arescore_foundry_lib/requirements.txt /tmp/arescore-lib-requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/orchestrator-requirements.txt \
    && python -m pip install -r /tmp/arescore-lib-requirements.txt

COPY services/_generated /app/services/_generated
COPY backend/arescore_foundry_lib /app/arescore_foundry_lib
COPY services/orchestrator/app /app/app

CMD ["python", "-m", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8080"]
