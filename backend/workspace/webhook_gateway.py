"""Expose exactly one authenticated webhook route through a local HTTPS tunnel."""
import hashlib
import hmac
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_BODY = 1024 * 1024


def make_gateway(connection_id, secret, upstream='http://127.0.0.1:8000'):
    path = f'/api/v1/hooks/github/{connection_id}/'

    def application(environ, start_response):
        def respond(status, value):
            body = json.dumps(value).encode()
            start_response(status, [('Content-Type', 'application/json'), ('Content-Length', str(len(body))), ('Cache-Control', 'no-store')])
            return [body]

        if environ.get('PATH_INFO') != path or environ.get('REQUEST_METHOD') != 'POST' or environ.get('QUERY_STRING'):
            return respond('404 Not Found', {'detail': 'Not found.'})
        if environ.get('HTTP_TRANSFER_ENCODING'):
            return respond('400 Bad Request', {'detail': 'Content-Length is required.'})
        try:
            size = int(environ.get('CONTENT_LENGTH', ''))
        except (ValueError, TypeError):
            return respond('400 Bad Request', {'detail': 'Invalid Content-Length.'})
        if size < 0 or size > MAX_BODY:
            return respond('413 Payload Too Large', {'detail': 'Payload too large.'})
        signature = environ.get('HTTP_X_HUB_SIGNATURE_256', '')
        if not re.fullmatch(r'sha256=[0-9a-f]{64}', signature):
            return respond('403 Forbidden', {'detail': 'Invalid signature.'})
        body = environ['wsgi.input'].read(size)
        if len(body) != size:
            return respond('400 Bad Request', {'detail': 'Incomplete payload.'})
        expected = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return respond('403 Forbidden', {'detail': 'Invalid signature.'})
        request = Request(upstream + path, data=body, method='POST', headers={
            'Content-Type': 'application/json',
            'X-Hub-Signature-256': signature,
            'X-GitHub-Delivery': environ.get('HTTP_X_GITHUB_DELIVERY', '')[:100],
            'X-GitHub-Event': environ.get('HTTP_X_GITHUB_EVENT', '')[:100],
        })
        try:
            with urlopen(request, timeout=10) as response:
                code, raw = response.status, response.read(MAX_BODY + 1)
        except HTTPError as error:
            code, raw = error.code, error.read(MAX_BODY + 1)
        except (URLError, OSError):
            return respond('503 Service Unavailable', {'detail': 'Webhook receiver unavailable.'})
        # Never relay debug pages, cookies, internal headers, or unexpected responses publicly.
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return respond('502 Bad Gateway', {'detail': 'Webhook receiver unavailable.'})
        if code >= 500 or not isinstance(result, dict):
            return respond('502 Bad Gateway', {'detail': 'Webhook receiver unavailable.'})
        messages = {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 410: 'Gone', 413: 'Payload Too Large'}
        if code not in messages:
            return respond('502 Bad Gateway', {'detail': 'Unexpected receiver response.'})
        return respond(f'{code} {messages[code]}', result)

    return application
