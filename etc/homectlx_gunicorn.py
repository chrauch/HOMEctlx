# Gunicorn configuration for HOMEctlx with WebSocket support
# Place in /srv/homectlx/etc/homectlx_gunicorn.py

import multiprocessing

# Bind to localhost only (Nginx will proxy)
bind = "127.0.0.1:5010"

# Single worker for WebSocket support (gevent handles concurrency)
workers = 1

# Use gevent worker for WebSocket support
worker_class = "gevent"

# Maximum number of simultaneous clients
worker_connections = 1000

# Timeout (set high for long-running operations)
timeout = 86400

# Logging
accesslog = "/srv/homectlx/share/temp/gunicorn-access.log"
errorlog = "/srv/homectlx/share/temp/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "homectlx"
