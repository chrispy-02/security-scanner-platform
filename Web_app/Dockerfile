# Vulnerability Detect and Analysis — production image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    FLASK_ENV=production \
    DOCKER_ENV=true

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application. Secrets are provided at runtime via env vars, never baked in
# (.dockerignore excludes any local .env).
COPY . /app

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Entrypoint seeds the schema/demo data (idempotent) then starts gunicorn.
# A single worker keeps the in-process scan scheduler from being duplicated and
# keeps the session key consistent across requests.
CMD ["sh", "./start.sh"]
