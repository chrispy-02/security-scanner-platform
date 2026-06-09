#!/bin/sh
# Container entrypoint: wait for the database, create schema + seed demo data
# (idempotent, retried until the DB is reachable), then serve.
n=0
until python seed_demo.py; do
  n=$((n + 1))
  if [ "$n" -ge 10 ]; then
    echo "seed_demo failed after $n attempts; starting the server anyway"
    break
  fi
  echo "database not ready (attempt $n); retrying in 3s..."
  sleep 3
done
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 8 --timeout 120 app:app
