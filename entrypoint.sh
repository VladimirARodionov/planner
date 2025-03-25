#!/usr/bin/env sh

if [ "$RUN_BOT" -eq 0 ]; then
  gunicorn -c /app/backend/gunicorn_config.py "backend.run:create_app_wsgi()"
else
  python -m "backend.run"
fi
