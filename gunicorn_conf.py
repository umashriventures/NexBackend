import multiprocessing

# Gunicorn configuration for high-performance FastAPI
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
timeout = 60
loglevel = "info"
accesslog = "-"
errorlog = "-"
