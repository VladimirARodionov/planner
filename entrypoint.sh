#!/usr/bin/env sh

if [ "$RUN_BOT" -eq 0 ]; then
  gunicorn --workers=2 --bind=0.0.0.0:5000 --timeout=60 "backend.run:create_app_wsgi()"
else
  python -m "backend.run"
fi
