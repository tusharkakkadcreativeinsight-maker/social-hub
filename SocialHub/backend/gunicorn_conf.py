import multiprocessing
import os
from app.config import settings

name = settings.APP_NAME

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5

errorlog = "-"
loglevel = "warning" if not settings.DEBUG else "debug"
accesslog = "-" if settings.DEBUG else None
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
