FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Bring in generated stubs and app code
COPY services/_generated /app/services/_generated
COPY services/orchestrator/app /app/app
COPY services/orchestrator/entrypoint.sh /entrypoint.sh

# Optional deps if present inside app/
RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi && \
    chmod +x /entrypoint.sh

ENV PYTHONPATH=/app
EXPOSE 8080

# Healthcheck without curl
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=2); print('ok')" || exit 1

CMD ["/entrypoint.sh"]
