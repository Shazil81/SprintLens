#!/usr/bin/env bash
set -euo pipefail
exec python -m gunicorn config.wsgi:application --config gunicorn.conf.py
