FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install orchestrator runtime dependencies first to leverage Docker layer caching.
COPY services/orchestrator/app/requirements.txt /tmp/orchestrator-requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/orchestrator-requirements.txt

COPY services/_generated /app/services/_generated
COPY arescore_foundry_lib /app/arescore_foundry_lib
RUN python -m pip install /app/arescore_foundry_lib

COPY services/orchestrator/app /app/app
COPY services/orchestrator/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c 'import urllib.request,sys; sys.exit(0 if urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2).getcode()==200 else 1)'
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
