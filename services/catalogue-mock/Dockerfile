FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9000

# Shell form, not exec form — needs the shell to expand $PORT. Render
# (and most PaaS Docker runtimes) inject their own PORT and route public
# traffic there; a hardcoded 9000 works for docker-compose but silently
# fails to bind the right port anywhere else.
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-9000}
