"""Configure local Gemini credentials without displaying them or placing them in shell history."""
import getpass
import json
import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Securely prompt for a Gemini API key and enable local insights. No network request is made.'

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR)/'.local.json'
        if not path.exists():
            raise CommandError('Run through local.py to initialize your private local configuration first.')
        key = getpass.getpass('Gemini API key (hidden): ').strip()
        if len(key) < 20 or any(character.isspace() for character in key):
            raise CommandError('The key format is invalid; configuration was not changed.')
        config = json.loads(path.read_text(encoding='utf-8'))
        config.update(gemini_api_key=key,ai_enabled=True)
        temporary = path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(config,indent=2),encoding='utf-8')
            os.replace(temporary,path)
        finally:
            temporary.unlink(missing_ok=True)
        self.stdout.write(self.style.SUCCESS('Local Gemini configuration saved. Restart the backend. Use an API project on the free tier; billing is controlled by Google.'))
