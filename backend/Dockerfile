# Backend-Image: FastAPI-API und die CLI-Skripte (ingest, analyze).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Abhaengigkeiten zuerst, damit der Layer-Cache greift.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode. synthetic_data und migrations werden per Volume/Compose gemountet.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
