FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*
# Copiar requirements del servicio
COPY services/users/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copiar shared (middleware, eventos, modelos compartidos)
COPY shared/ ./shared/
# Copiar código del servicio
COPY services/users/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
