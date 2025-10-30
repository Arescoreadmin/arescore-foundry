FROM python:3.11-slim
RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app
RUN python - <<'PY'
import py_compile
py_compile.compile("app/main.py", cfile="/tmp/main.pyc", doraise=True)
print("compile OK")
PY
RUN chown -R appuser:appuser /app
USER appuser
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
