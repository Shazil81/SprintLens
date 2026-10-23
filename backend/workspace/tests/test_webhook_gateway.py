import hashlib
import hmac
import io
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch
from urllib.error import URLError
from ..webhook_gateway import make_gateway


class GatewayTests(TestCase):
    def request(self, path='/api/v1/hooks/github/connection/', body=b'{}', method='POST', secret='test-secret', signature=None, overrides=None):
        app = make_gateway('connection', 'test-secret')
        status = []
        headers = []
        def start(value, values):
            status.append(value); headers.extend(values)
        signature = signature or 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        environ = {'PATH_INFO': path, 'REQUEST_METHOD': method, 'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body), 'HTTP_X_HUB_SIGNATURE_256': signature, 'HTTP_X_GITHUB_DELIVERY': 'delivery-1', 'HTTP_X_GITHUB_EVENT': 'ping'}
        environ.update(overrides or {})
        output = b''.join(app(environ, start))
        return status[0], json.loads(output), headers

    @patch('workspace.webhook_gateway.urlopen')
    def test_only_exact_signed_post_route_is_forwarded(self, upstream):
        response = MagicMock(status=200)
        response.read.return_value = b'{"accepted":true,"activities":0}'
        upstream.return_value.__enter__.return_value = response
        self.assertEqual(self.request()[0], '200 OK')
        request = upstream.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:8000/api/v1/hooks/github/connection/')
        self.assertNotIn('Cookie', request.headers)

    @patch('workspace.webhook_gateway.urlopen')
    def test_api_login_debug_and_other_paths_are_not_forwarded(self, upstream):
        for path in ['/', '/api/v1/tasks/', '/api/v1/auth/login/', '/admin/', '/api/v1/hooks/github/other/']:
            self.assertEqual(self.request(path=path)[0], '404 Not Found')
        self.assertEqual(self.request(method='GET')[0], '404 Not Found')
        upstream.assert_not_called()

    @patch('workspace.webhook_gateway.urlopen')
    def test_missing_invalid_or_tampered_signature_is_rejected(self, upstream):
        self.assertEqual(self.request(signature='invalid')[0], '403 Forbidden')
        self.assertEqual(self.request(secret='wrong-secret')[0], '403 Forbidden')
        upstream.assert_not_called()

    @patch('workspace.webhook_gateway.urlopen')
    def test_debug_response_is_sanitized(self, upstream):
        response = MagicMock(status=200)
        response.read.return_value = b'<html>Internal debug settings</html>'
        upstream.return_value.__enter__.return_value = response
        status, body, headers = self.request()
        self.assertEqual(status, '502 Bad Gateway')
        self.assertNotIn('Internal', str(body))
        self.assertEqual(dict(headers)['Cache-Control'], 'no-store')

    @patch('workspace.webhook_gateway.urlopen', side_effect=URLError('internal details'))
    def test_unavailable_api_does_not_leak_details(self, upstream):
        self.assertEqual(self.request()[:2], ('503 Service Unavailable', {'detail': 'Webhook receiver unavailable.'}))

    @patch('workspace.webhook_gateway.urlopen')
    def test_invalid_size_chunked_incomplete_and_query_requests_are_rejected(self, upstream):
        cases = [({'CONTENT_LENGTH': '1048577'}, '413 Payload Too Large'),
                 ({'CONTENT_LENGTH': '-1'}, '413 Payload Too Large'),
                 ({'CONTENT_LENGTH': 'invalid'}, '400 Bad Request'),
                 ({'CONTENT_LENGTH': '4'}, '400 Bad Request'),
                 ({'HTTP_TRANSFER_ENCODING': 'chunked'}, '400 Bad Request'),
                 ({'QUERY_STRING': 'redirect=elsewhere'}, '404 Not Found')]
        for overrides, expected in cases:
            self.assertEqual(self.request(overrides=overrides)[0], expected)
        upstream.assert_not_called()
