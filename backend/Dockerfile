FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY infra/seed /app/seed
RUN chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000
# API uses entrypoint (migrate + uvicorn). Worker/beat override command.
CMD ["/app/scripts/entrypoint.sh"]
