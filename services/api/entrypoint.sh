#!/bin/sh
# Runs on every container start, anywhere this image runs (Render, local
# docker-compose, elsewhere) - both steps are idempotent (alembic no-ops
# once up to date; scripts.seed_users get-or-creates every account), so
# running them on every boot is safe, not just a one-time setup step.
# This replaces needing a separate one-off "run migrations" command after
# every deploy, which isn't available at all on Render's free plan (its
# Jobs API requires a paid plan) and is easy to forget to run by hand
# anywhere else.
set -e

echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] seeding RBAC + demo accounts..."
python -m scripts.seed_users

echo "[entrypoint] starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
