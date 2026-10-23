from wsgiref.simple_server import WSGIRequestHandler, make_server
from django.core.management.base import BaseCommand, CommandError
from workspace.github import webhook_secret
from workspace.models import GitHubConnection
from workspace.webhook_gateway import make_gateway


class QuietHandler(WSGIRequestHandler):
    def handle(self):
        self.connection.settimeout(15)
        super().handle()

    def log_message(self, format, *args):
        # Never print incoming headers, payloads or webhook secrets.
        pass


class Command(BaseCommand):
    help = 'Serve only one signed GitHub webhook on loopback for temporary HTTPS tunnel testing.'

    def add_arguments(self, parser):
        parser.add_argument('--repository', required=True)
        parser.add_argument('--port', type=int, default=8091)

    def handle(self, *args, **options):
        connection = GitHubConnection.objects.filter(repository=options['repository'].lower(), enabled=True).first()
        if not connection:
            raise CommandError('Configure an enabled repository connection in SprintLens first.')
        app = make_gateway(connection.pk, webhook_secret(connection))
        self.stdout.write(f'Webhook-only gateway: http://127.0.0.1:{options["port"]}/api/v1/hooks/github/{connection.pk}/')
        self.stdout.write('All other routes are rejected. Stop with Ctrl+C.')
        with make_server('127.0.0.1', options['port'], app, handler_class=QuietHandler) as server:
            server.serve_forever()
