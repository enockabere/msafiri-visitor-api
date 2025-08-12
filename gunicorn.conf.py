import os

bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
workers = int(os.getenv('WEB_CONCURRENCY', 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
