#!/bin/sh
set -e

uv run flask db upgrade

exec uv run gunicorn -w 4 -b 0.0.0.0:5000 app:app
