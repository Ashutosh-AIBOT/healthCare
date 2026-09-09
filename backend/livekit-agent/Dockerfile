FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py groq_llm.py key_loader.py ./

# HF Spaces expects HTTP on 7860 (health check); worker runs alongside.
EXPOSE 7860

CMD ["sh", "-c", "python agent.py start & python -m http.server 7860"]
