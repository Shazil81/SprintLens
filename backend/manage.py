#!/usr/bin/env python
import os
import sys
from pathlib import Path


def use_local_runserver(arguments, environment, local_config_exists):
    """Support the familiar local command without weakening explicit production configuration."""
    return (
        arguments[:1] == ['runserver']
        and local_config_exists
        and environment.get('DJANGO_DEBUG', '').lower() not in {'0', 'false'}
        and not any(environment.get(key) for key in
                    ['RENDER', 'DJANGO_SECRET_KEY', 'DATABASE_URL', 'DJANGO_SETTINGS_MODULE'])
    )

if __name__ == '__main__':
    if use_local_runserver(sys.argv[1:], os.environ, Path(__file__).with_name('.local.json').is_file()):
        from local_environment import configure_environment
        configure_environment()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
