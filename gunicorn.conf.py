bind = "0.0.0.0:7002"
workers = 2
threads = 4
worker_class = "uvicorn.workers.UvicornH11Worker"
timeout = 30
keepalive = 2
