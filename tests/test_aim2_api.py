"""Local fake HTTP service only; never connects to AIM2 or a broker."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1] / 'skills/aim2-api/scripts/aim2_api.py'
spec = importlib.util.spec_from_file_location('aim2_api', CLIENT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Handler(BaseHTTPRequestHandler):
    records: list[tuple[str, str | None, bytes]] = []

    def do_GET(self) -> None:
        self.records.append((self.path, self.headers.get('Authorization'), b''))
        if self.path == '/api/redirect':
            self.send_response(302)
            self.send_header('Location', '/stolen')
            self.end_headers()
            return
        if self.path == '/api/error':
            self.send_response(409)
            self.end_headers()
            self.wfile.write(b'secret-server-error')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html' if self.path == '/api/spa' else 'application/json')
        self.send_header('Content-Length', '100' if self.path == '/api/truncated' else '2')
        self.end_headers()
        self.wfile.write(b'[]')

    def do_POST(self) -> None:
        data = self.rfile.read(int(self.headers['Content-Length']))
        self.records.append((self.path, self.headers.get('Authorization'), data))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


class ApiClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.token = self.root / 'token'
        self.token.write_text('test-private-token\n')
        Handler.records = []
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = {**os.environ, 'AIM2_API_BASE': f'http://127.0.0.1:{self.server.server_port}/api',
                    'AIM2_TOKEN_FILE': str(self.token)}

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def run_client(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, str(CLIENT), *args], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertNotIn('test-private-token', result.stdout + result.stderr)
        return result

    def test_prefix_auth_and_streamed_file(self) -> None:
        output = self.root / 'out.json'
        result = self.run_client('GET', '/baskets?limit=1', '--allow-http', '--output', str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_text(), '[]')
        self.assertEqual(Handler.records, [('/api/baskets?limit=1', 'Bearer test-private-token', b'')])
        self.assertEqual(result.stdout, '')

    def test_post_payload_and_no_retry(self) -> None:
        source = self.root / 'input.json'
        source.write_text('{"text":"привет"}')
        result = self.run_client('POST', '/baskets', '--allow-http', '--json-file', str(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'text': 'привет'})
        self.assertEqual(len(Handler.records), 1)

    def test_redirect_is_not_followed(self) -> None:
        result = self.run_client('GET', '/redirect', '--allow-http')
        self.assertEqual(result.returncode, 1)
        self.assertIn('302', result.stderr)
        self.assertEqual(len(Handler.records), 1)

    def test_error_body_is_not_logged_or_saved(self) -> None:
        output = self.root / 'error.json'
        result = self.run_client('GET', '/error', '--allow-http', '--output', str(output))
        self.assertEqual(result.returncode, 1)
        self.assertIn('409', result.stderr)
        self.assertNotIn('secret-server-error', result.stdout + result.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(len(Handler.records), 1)

    def test_http_requires_explicit_opt_in(self) -> None:
        result = self.run_client('GET', '/baskets')
        self.assertEqual(result.returncode, 1)
        self.assertFalse(Handler.records)

    def test_existing_output_is_preserved(self) -> None:
        output = self.root / 'existing.json'
        output.write_text('keep')
        result = self.run_client('GET', '/baskets', '--allow-http', '--output', str(output))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output.read_text(), 'keep')
        self.assertFalse(Handler.records)

    def test_reject_non_finite_json_before_request(self) -> None:
        source = self.root / 'bad.json'
        source.write_text('{"value":NaN}')
        result = self.run_client('POST', '/baskets', '--allow-http', '--json-file', str(source))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(Handler.records)

    def test_no_partial_or_spa_output(self) -> None:
        for route in ('/truncated', '/spa'):
            with self.subTest(route=route):
                output = self.root / 'bad-output.json'
                result = self.run_client('GET', route, '--allow-http', '--output', str(output))
                self.assertEqual(result.returncode, 1)
                self.assertFalse(output.exists())
                self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['token'])

    def test_absolute_and_traversal_routes_rejected(self) -> None:
        for route in ('https://other.example/a', '//other.example/a', '/../a', '/%2e%2e/a', '/a#fragment'):
            with self.subTest(route=route):
                with self.assertRaises(ValueError):
                    module.endpoint('https://aim2.example/api', route, False)
        self.assertEqual(module.endpoint('https://aim2.example/api/', '/baskets', False),
                         'https://aim2.example/api/baskets')


if __name__ == '__main__':
    unittest.main()
