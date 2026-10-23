"""Load private local settings for the API, management commands and Celery."""
import json
import os
import secrets
from pathlib import Path
from urllib.parse import quote


def configure_environment():
    if os.getenv('RENDER'):
        raise RuntimeError('Local configuration is disabled on Render. Use manage.py and production environment variables.')
    root = Path(__file__).resolve().parent
    path = root / '.local.json'
    if not path.exists():
        path.write_text(json.dumps({'secret_key': secrets.token_urlsafe(48), 'demo_password': secrets.token_urlsafe(18), 'postgres_password': secrets.token_urlsafe(24), 'use_postgres': False}, indent=2))
    config = json.loads(path.read_text())
    os.environ['DJANGO_DEBUG'] = '1'
    os.environ['DJANGO_SECRET_KEY'] = config['secret_key']
    os.environ['SPRINTLENS_DEMO_PASSWORD'] = config['demo_password']
    if config.get('gemini_api_key'):
        os.environ.setdefault('GEMINI_API_KEY',config['gemini_api_key'])
    if config.get('ai_enabled'):
        os.environ.setdefault('AI_INSIGHTS_ENABLED','1')
    if config.get('gemini_model'):
        os.environ.setdefault('GEMINI_MODEL',config['gemini_model'])
    if config.get('database'):
        # Encode credentials because passwords may contain URL-reserved characters.
        database = config['database']
        os.environ['DATABASE_URL'] = (
            f"postgresql://{quote(database['user'], safe='')}:{quote(database['password'], safe='')}"
            f"@{database['host']}:{database['port']}/{quote(database['name'], safe='')}"
        )
    elif config.get('use_postgres'):
        os.environ['DATABASE_URL'] = 'postgresql://sprintlens:' + config['postgres_password'] + '@127.0.0.1:5433/sprintlens'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
