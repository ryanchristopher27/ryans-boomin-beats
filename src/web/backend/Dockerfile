# Hosted instance of the Boomin Beats API (D1).
# Build context is this directory:  docker build -t boomin-api src/web/backend
#
# The same image serves the local instance; the only difference is configuration
# — set DEVICE_KEY here and leave it unset locally.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Imports are flat (`from config import ...`), so /app must be the working dir.
# $PORT is provided by Fly/Render/Railway; 8005 matches local dev as a fallback.
EXPOSE 8005
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8005}
