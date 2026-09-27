FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8000

# entrypoint.sh runs migrations + the idempotent seed script before
# starting uvicorn on every boot — see that file's own comment for why
# this replaces a separate one-off "run migrations after deploy" step
# (not available at all on Render's free plan, easy to forget by hand
# anywhere else). It also handles $PORT the same way the previous direct
# CMD did: unset locally (falls back to 8000, matching docker-compose's
# fixed mapping), set on Render/most PaaS Docker runtimes (uses whatever
# they assign).
CMD ["./entrypoint.sh"]
