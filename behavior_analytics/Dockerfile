FROM python:3.11-slim
WORKDIR /app
COPY behavior_analytics /app
RUN pip install fastapi uvicorn requests pydantic pydantic-settings
EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
