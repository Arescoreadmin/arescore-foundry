FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install orchestrator + shared lib deps
COPY services/orchestrator/app/requirements.txt /tmp/orchestrator-requirements.txt
COPY arescore_foundry_lib/requirements.txt /tmp/arescore-lib-requirements.txt

RUN python -m pip install --upgrade pip && \
    pip install -r /tmp/orchestrator-requirements.txt -r /tmp/arescore-lib-requirements.txt

# Generated API code
COPY services/_generated /app/services/_generated

# Shared library (exports logging_setup, etc.)
COPY arescore_foundry_lib /app/arescore_foundry_lib
RUN python -m pip install /app/arescore_foundry_lib || true

# Orchestrator app
COPY services/orchestrator/app /app/app

# Entrypoint
COPY services/orchestrator/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c 'import urllib.request,sys; sys.exit(0 if urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2).getcode()==200 else 1)'

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
