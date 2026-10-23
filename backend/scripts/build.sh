#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.lock.txt
python manage.py check
# This API-only backend has no frontend/static assets to collect.
