from fastapi import FastAPI

app = FastAPI(title="Aarogya API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/ready")
def ready():
    return {"status": "ready"}
