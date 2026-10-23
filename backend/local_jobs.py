"""Run Celery locally with the same private settings as the API."""
import sys
from local_environment import configure_environment

configure_environment()
from config.celery import app

if __name__ == "__main__":
    app.start(sys.argv[1:])
