# gunicorn.conf.py
import multiprocessing

# Número de workers: 1 é suficiente para o plan gratuíto
workers = 1

# Usar o worker sincrono (máis lixeiro)
worker_class = 'sync'

# Tempo máximo de resposta (evita timeouts)
timeout = 120

# Número de peticións antes de reiniciar un worker (libera memoria)
max_requests = 100
max_requests_jitter = 10

# Logs
accesslog = '-'
errorlog = '-'
loglevel = 'info'