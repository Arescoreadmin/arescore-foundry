FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# orchestrator deps
COPY services/orchestrator/app/requirements.txt /tmp/orchestrator-requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/orchestrator-requirements.txt

# shared lib
COPY services/_generated /app/services/_generated
COPY arescore_foundry_lib /app/arescore_foundry_lib
RUN python -m pip install /app/arescore_foundry_lib

# orchestrator app
COPY services/orchestrator/app /app/app
COPY services/orchestrator/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

HEALTHCHECK ...   # keep whatever the PR had here
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
