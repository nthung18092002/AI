import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from localstudio.engine import plan
from localstudio.network import local_url, open_local


class LocalAITests(unittest.TestCase):
    def test_remote_endpoints_rejected(self):
        for url in ['https://api.openai.com', 'http://example.com', 'http://127.0.0.1.evil.test', 'http://user:pass@localhost', 'file:///etc/passwd']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                local_url(url)

    def test_ollama_protocol_and_unload(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/api/show':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"details":{"format":"gguf"}}')
                    return
                captured.append(body)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'response': json.dumps({'lines': ['Khám phá sản phẩm.', 'Ảnh sản phẩm thực tế.', 'Đọc thông tin trước khi mua.', 'Xem liên kết đính kèm.']})}).encode())
            def do_GET(self):
                self.send_response(302)
                self.send_header('Location', 'https://example.com/')
                self.end_headers()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            result = plan({'product': 'Đèn', 'prompt': 'Bàn học', 'duration': 20, 'use_ollama': True, 'ollama_url': base})
            self.assertEqual(len(result['lines']), 4)
            self.assertEqual(captured[0]['keep_alive'], 0)
            self.assertFalse(captured[0]['stream'])
            with self.assertRaisesRegex(ValueError, 'từ xa'):
                plan({'prompt': 'Test', 'duration': 20, 'use_ollama': True, 'ollama_model': 'remote:cloud', 'ollama_url': base})
            self.assertEqual(len(captured), 1)
            with self.assertRaises(ValueError):
                open_local(base + '/redirect')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
