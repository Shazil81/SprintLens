#!/usr/bin/env bash
set -euo pipefail
python manage.py check --deploy --fail-level ERROR
python manage.py migrate --noinput
python manage.py migrate --check
