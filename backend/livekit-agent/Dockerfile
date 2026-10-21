FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py groq_llm.py key_loader.py ./

# Render/HF health check: $PORT is injected by Render; default 7860 elsewhere.
# The worker runs in the foreground so container logs stay attached; the
# health server is a background companion only (worker needs no inbound port).
EXPOSE 7860

CMD ["sh", "-c", "python -m http.server ${PORT:-7860} & exec python agent.py start"]
