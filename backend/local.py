"""Run local Django commands with private development settings."""
import sys
from pathlib import Path
from local_environment import configure_environment

configure_environment()
from django.core.management import execute_from_command_line
execute_from_command_line([str(Path(__file__).with_name("manage.py")), *sys.argv[1:]])
