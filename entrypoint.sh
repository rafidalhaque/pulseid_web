#!/bin/sh
set -e

uv run flask db upgrade

LOG_LEVEL="info"
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "True" ] || [ "$DEBUG" = "1" ]; then
  LOG_LEVEL="debug"
fi

exec uv run gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - --log-level "$LOG_LEVEL" app:app
