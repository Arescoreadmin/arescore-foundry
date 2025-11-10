FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/_generated /app/services/_generated
COPY services/common /app/services/common
COPY services/audit_collector/app /app/app
COPY services/audit_collector/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && python -m pip install --upgrade pip \
    && pip install -r /app/app/requirements.txt
ENTRYPOINT ["/entrypoint.sh"]
