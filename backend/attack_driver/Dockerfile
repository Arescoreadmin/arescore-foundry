FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY driver.py /app/driver.py
EXPOSE 8084
CMD ["uvicorn","driver:app","--host","0.0.0.0","--port","8084"]
