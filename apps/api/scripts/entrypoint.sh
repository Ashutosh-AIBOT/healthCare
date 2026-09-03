#!/bin/sh
set -e
echo "[entrypoint] waiting for database..."
python - <<'PY'
import os, time, sys
from urllib.parse import urlparse
import socket

url = os.environ.get("MIGRATE_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
# postgresql+asyncpg://user:pass@host:port/db
raw = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", "")
# host:port from after @
try:
    after = raw.split("@", 1)[1]
    hostport = after.split("/", 1)[0]
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "5432")
except Exception:
    host, port = "postgres", "5432"

for i in range(60):
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            print(f"[entrypoint] database reachable at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(1)
print("[entrypoint] database not reachable", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] alembic upgrade head"
alembic upgrade head

echo "[entrypoint] starting api"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
