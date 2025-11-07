FROM python:3.11-slim

RUN useradd -m appuser
WORKDIR /app

COPY backend/frostgatecore/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/frostgatecore/app/ /app/app/

USER appuser
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
