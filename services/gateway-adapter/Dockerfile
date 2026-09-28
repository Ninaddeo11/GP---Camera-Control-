FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9100

# Shell form so $PORT expands — most PaaS Docker runtimes (Render
# included) inject their own port and route public traffic there.
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-9100}
