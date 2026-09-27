FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render (and most PaaS Docker runtimes) inject a $PORT env var and expect
# the container to listen on it, which docker-compose's fixed 8000:8000
# mapping never needed — shell form + ${PORT:-8000} keeps both working:
# unset locally (falls back to 8000, matching docker-compose), set on
# Render (uses whatever it assigns).
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
