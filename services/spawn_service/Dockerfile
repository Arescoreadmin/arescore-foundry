FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/_generated /app/services/_generated
COPY services/spawn_service/app /app/app

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi

ENV PYTHONPATH=/app
CMD ["python", "-m", "app.main"]
