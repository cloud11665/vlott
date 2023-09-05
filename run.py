#!/usr/bin/env python3
import os

def envor(x, y):
	os.environ[x] = os.environ.get(x, y)
	return os.environ[x]

LEGACY_ADDR = envor("VLOTT_LEGACY_ADDR", "127.0.0.1:7002")
WORKERS = envor("VLOTT_WORKERS", "1")
V1_ENABLED = envor("VLOTT_USE_V1", "1")
PORT = envor("VLOTT_PORT", "80")

if __name__ == "__main__":
	os.system(f"gunicorn -k uvicorn.workers.UvicornWorker app:app --log-level warn -w {WORKERS} -b 0.0.0.0:{PORT}")
