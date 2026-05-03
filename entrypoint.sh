#!/bin/sh
set -e

uv run flask db upgrade

exec uv run gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - --log-level debug app:app
