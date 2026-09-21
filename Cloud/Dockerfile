FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/Program:/app

WORKDIR /app

COPY Cloud/requirements.txt /app/Cloud/requirements.txt
RUN pip install --no-cache-dir -r /app/Cloud/requirements.txt

COPY Program /app/Program
COPY Cloud /app/Cloud

EXPOSE 8080

CMD ["uvicorn", "cloud.app:app", "--host", "0.0.0.0", "--port", "8080"]
