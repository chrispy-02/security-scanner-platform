#!/bin/sh
# Start the web server immediately so the platform detects the open port. Seed the
# schema + demo data (idempotent, with retry) in the BACKGROUND so a slow/unready
# database can't block the port bind. Data appears once seeding finishes.
seed() {
  n=0
  until python seed_demo.py; do
    n=$((n + 1))
    if [ "$n" -ge 10 ]; then
      echo "seed_demo failed after $n attempts; giving up (server stays up)"
      return
    fi
    echo "database not ready (attempt $n); retrying in 5s..."
    sleep 5
  done
}
seed &
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 8 --timeout 120 app:app
