import hashlib
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from localstudio.assets import download_verified
from localstudio.engine import ROOT, comfy_generate, ffmpeg, frame_budgets, render
from localstudio.process import Cancelled, execute
from localstudio.speech import espeak_speech, wave_seconds
from localstudio.workflows import validate_graph, wan_workflow
from PIL import Image


class PipelineTests(unittest.TestCase):
    def test_cancel_running_subprocess(self):
        import sys
        import time
        start = time.monotonic()
        with self.assertRaises(Cancelled):
            execute([sys.executable, '-c', 'import time; time.sleep(20)'], cancel=lambda: time.monotonic() - start > .15)
        self.assertLess(time.monotonic() - start, 3)

    def test_voice_is_real_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'speech.wav'
            espeak_speech('Xin chào. Đây là lời đọc tiếng Việt chạy trên máy.', path)
            self.assertGreater(wave_seconds(path), 1)
            self.assertGreater(path.stat().st_size, 10000)

    def test_duration_allocation(self):
        for duration in (20, 30, 40):
            budget = frame_budgets(duration, [1, 4, 2, 7, 1.5])
            self.assertEqual(sum(budget), duration * 24)
            self.assertTrue(all(x >= 24 for x in budget))
            self.assertGreater(budget[3], budget[0])

    def test_cancellation_before_work(self):
        with self.assertRaises(Cancelled):
            render({'prompt': 'Test', 'duration': 20}, {}, lambda _: None, cancel=lambda: True)

    def test_download_integrity_and_no_overwrite(self):
        payload = b'known verified model bytes'
        expected = hashlib.sha256(payload).hexdigest()
        class Response(io.BytesIO):
            url = 'https://huggingface.co/test'
            headers = {'Content-Length': str(len(payload))}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'model.bin'
            with patch('localstudio.assets.https_open', return_value=Response(payload)):
                download_verified('https://huggingface.co/test', target, expected)
            self.assertEqual(target.read_bytes(), payload)
            target.write_bytes(b'corrupted')
            with self.assertRaises(RuntimeError):
                download_verified('https://huggingface.co/test', target, expected)
            self.assertEqual(target.read_bytes(), b'corrupted')
            target.unlink()
            with patch('localstudio.assets.https_open', return_value=Response(b'bad')):
                with self.assertRaises(RuntimeError):
                    download_verified('https://huggingface.co/test', target, expected)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_name('model.bin.partial').exists())

    def test_cloud_workflow_rejected_before_request(self):
        graph = {'1': {'class_type': 'OpenAICloudVideo', 'inputs': {'prompt': '{{PROMPT}}'}}}
        with patch('localstudio.engine.request_json') as request:
            with self.assertRaisesRegex(ValueError, 'chưa được chấp nhận'):
                comfy_generate(graph, 'Private product', 'http://127.0.0.1:8188', Path('.'), 0)
            request.assert_not_called()

    def test_remote_ollama_alias_rejected_before_generation(self):
        from localstudio.engine import plan
        with patch('localstudio.engine.request_json', return_value={'remote_host': 'https://ollama.com', 'details': {'format': 'gguf'}}) as request:
            with self.assertRaisesRegex(ValueError, 'từ xa'):
                plan({'prompt': 'Private product', 'use_ollama': True, 'ollama_model': 'innocent-alias'})
            self.assertEqual(request.call_count, 1)
            self.assertTrue(request.call_args.args[0].endswith('/api/show'))
            self.assertNotIn('Private product', json.dumps(request.call_args.args))

    def test_missing_comfy_nodes_fail(self):
        with self.assertRaisesRegex(ValueError, 'Thiếu node'):
            validate_graph(wan_workflow(), {})

    def test_comfy_protocol_and_full_mux_with_fixture(self):
        # This server is a protocol fixture, NOT an AI model. Exercise the real video pipeline.
        captured = []
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / 'fixture.webm'
            subprocess.run([ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=160x288:rate=16:duration=0.5', '-c:v', 'libvpx-vp9', str(fixture)], check=True)
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass
                def do_POST(self):
                    captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                    self.send_response(200);self.end_headers()
                    self.wfile.write(b'{"prompt_id":"fixture"}')
                def do_GET(self):
                    self.send_response(200);self.end_headers()
                    if self.path.startswith('/view'):
                        self.wfile.write(fixture.read_bytes())
                    else:
                        self.wfile.write(json.dumps({'fixture': {'outputs': {'1': {'images': [{'filename': 'fixture.webm', 'type': 'output'}]}}, 'status': {'status_str': 'success'}}}).encode())
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
            try:
                blob = io.BytesIO();Image.new('RGB', (100, 180), '#df8844').save(blob, 'PNG');blob.seek(0)
                result = render({'prompt': 'Warm studio', 'product': 'Sản phẩm mẫu', 'duration': 20, 'mode': 'comfy', 'workflow': {'1': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{PROMPT}}'}}}, 'comfy_url': f'http://127.0.0.1:{server.server_port}', 'speech': 'espeak', 'auto_music': True, 'product_overlay': False}, {'images': [blob]}, lambda _: None, width=180, height=320)
                self.assertEqual(len(captured), 4)
                self.assertNotIn('{{PROMPT}}', json.dumps(captured))
                path = ROOT / result['video'].lstrip('/')
                probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
                meta = json.loads(probe.stdout)
                self.assertAlmostEqual(float(meta['format']['duration']), 20, delta=.1)
                self.assertEqual({x['codec_type'] for x in meta['streams']}, {'audio', 'video'})
                subprocess.run([ffmpeg(), '-v', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
            finally:
                server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
