"""Local desktop browser application. AI endpoints are restricted to loopback."""
import argparse
import base64
import io
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import uuid
import urllib.parse
import webbrowser
import sys

from localstudio.engine import ROOT, render, validate
from localstudio.process import Cancelled, stop_processes
from localstudio.services import start_services, system_status
from localstudio import projects

jobs, signals = {}, {}
lock = threading.RLock()
HISTORY = ROOT / 'work' / 'jobs.json'


def persist():
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    temporary = HISTORY.with_suffix('.tmp')
    temporary.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(HISTORY)


def update_job(key, **values):
    with lock:
        jobs[key].update(values)
        persist()


def load_history():
    if HISTORY.is_file():
        try:
            previous = json.loads(HISTORY.read_text(encoding='utf-8'))
            for key, value in list(previous.items())[-100:]:
                if value.get('status') == 'running':
                    value.update(status='interrupted', error='Ứng dụng đã dừng trước khi hoàn tất. Hãy tạo lại video.')
                jobs[key] = value
        except (ValueError, OSError):
            pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Request paths contain only local IDs. Never log uploaded product data.
        pass

    def local_request(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.local_request():
            return self.reply(403, {'error': 'Host rejected'})
        url = urllib.parse.urlsplit(self.path)
        if url.path == '/api/system':
            return self.reply(200, system_status())
        if re.fullmatch(r'/api/reference/[a-f0-9]{32}', url.path):
            try:
                return self.reply(200, projects.describe(url.path.rsplit('/', 1)[-1]))
            except (ValueError, OSError) as exc:
                return self.reply(404, {'error': str(exc)})
        if url.path == '/api/jobs':
            with lock:
                return self.reply(200, list(jobs.values())[-50:][::-1])
        if url.path.startswith('/api/jobs/'):
            with lock:
                job = jobs.get(url.path.split('/')[-1])
                return self.reply(200 if job else 404, job or {'error': 'Không tìm thấy tác vụ'})
        if url.path == '/studio.js':
            path = ROOT / 'web/studio.js'
        elif url.path == '/':
            path = ROOT / 'web' / 'index.html'
        elif re.fullmatch(r'/projects/[a-f0-9]{32}/(?:frame-\d+\.png|voice-\d+\.wav|preview-\d+\.mp4)', url.path):
            parts = url.path.strip('/').split('/')
            path = projects.project_folder(parts[1]) / parts[2]
        elif re.fullmatch(r'/outputs/[a-f0-9]{32}\.(mp4|srt|json)', url.path):
            path = ROOT / url.path.lstrip('/')
        else:
            return self.reply(404, {'error': 'Not found'})
        if not path.is_file():
            return self.reply(404, {'error': 'Not found'})
        size, start, end = path.stat().st_size, 0, path.stat().st_size - 1
        partial = self.headers.get('Range')
        if partial:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', partial)
            if not match or not any(match.groups()):
                return self.reply(416, {'error': 'Invalid byte range'})
            if match.group(1):
                start = int(match.group(1))
                end = min(end, int(match.group(2))) if match.group(2) else end
            else:
                start = max(0, size - int(match.group(2)))
            if start > end or start >= size:
                return self.reply(416, {'error': 'Invalid byte range'})
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', 'text/html; charset=utf-8' if path.suffix == '.html' else mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        if url.query == 'download=1':
            self.send_header('Content-Disposition', f'attachment; filename="{path.name}"')
        self.end_headers()
        try:
            with path.open('rb') as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = source.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not self.local_request() or self.headers.get('Origin') not in (None, f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.reply(403, {'error': 'Local requests only'})
        if not self.headers.get('Content-Type', '').startswith('application/json'):
            return self.reply(415, {'error': 'JSON required'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 100 * 1024 * 1024:
                raise ValueError('Tổng dữ liệu tải lên tối đa 100 MB.')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Request phải là JSON object.')
            if re.fullmatch(r'/api/jobs/[a-f0-9]{32}/cancel', self.path):
                key = self.path.split('/')[3]
                with lock:
                    if key not in signals or jobs[key].get('status') != 'running':
                        return self.reply(409, {'error': 'Tác vụ không còn chạy.'})
                    signals[key].set()
                return self.reply(202, {'message': 'Đã yêu cầu hủy. Đợi bước đang chạy kết thúc; không tắt đột ngột ComfyUI.'})
            if re.fullmatch(r'/api/reference/(prepare|approve|preview|approve-motion|export|delivery)', self.path):
                return self.reference_request(self.path.rsplit('/', 1)[-1], data)
            if self.path != '/api/render':
                return self.reply(404, {'error': 'Not found'})
            validate(data)
            if len(data.get('images', [])) > 12:
                raise ValueError('Tối đa 12 ảnh mỗi video.')
            if data.get('mode', 'photos') == 'photos' and not data.get('images'):
                raise ValueError('Hãy chọn ảnh sản phẩm hoặc chuyển sang chế độ AI.')
            with lock:
                if any(j.get('status') == 'running' for j in jobs.values()):
                    return self.reply(409, {'error': 'Một video đang được xử lý. Hãy chờ hoàn tất hoặc hủy.'})
                key = uuid.uuid4().hex
                jobs[key] = {'id': key, 'title': str(data.get('product') or data['prompt'])[:100], 'status': 'running', 'message': 'Đang chuẩn bị'}
                signals[key] = threading.Event()
                persist()
            def work():
                try:
                    import tempfile
                    with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
                        uploads = {'images': []}
                        for encoded in data.pop('images', []):
                            uploads['images'].append(io.BytesIO(base64.b64decode(encoded, validate=True)))
                        for name in ('narration', 'music'):
                            if data.get(name):
                                path = Path(temporary) / (name + '.audio')
                                path.write_bytes(base64.b64decode(data.pop(name), validate=True))
                                uploads[name] = path
                        result = render(data, uploads, lambda msg: update_job(key, message=msg), cancel=signals[key].is_set)
                    update_job(key, status='done', message='Đã xuất video', **result)
                except Cancelled as exc:
                    update_job(key, status='cancelled', error=str(exc))
                except Exception as exc:
                    update_job(key, status='error', error=str(exc))
                finally:
                    with lock:
                        signals.pop(key, None)
            threading.Thread(target=work, daemon=True).start()
            self.reply(202, {'id': key})
        except Exception as exc:
            self.reply(400, {'error': str(exc)})


    def reference_request(self, action, data):
        with lock:
            if any(job.get('status') == 'running' for job in jobs.values()):
                return self.reply(409, {'error': 'Có tác vụ đang chạy. Chờ hoặc hủy trước khi thay đổi dự án.'})
            if action in ('approve', 'approve-motion', 'delivery'):
                if action == 'delivery':
                    result = projects.set_delivery(data['project_id'], data.get('speech_delivery'))
                elif action == 'approve':
                    result = projects.approve_frames(data['project_id'], data.get('frame_hashes'))
                else:
                    result = projects.approve_preview(data['project_id'], data.get('preview_sha256'), data.get('scene_index', 0))
                return self.reply(200, result)
            if action == 'prepare':
                validate(data)
                if len(data.get('images', [])) != 1:
                    raise ValueError('Chế độ tham chiếu cần đúng một ảnh sản phẩm chuẩn cho mỗi dự án.')
            else:
                projects.read(data['project_id'])
            key = uuid.uuid4().hex
            jobs[key] = {'id': key, 'title': str(data.get('product') or action), 'status': 'running', 'message': 'Đang chuẩn bị dự án tham chiếu', 'action': action}
            signals[key] = threading.Event()
            persist()
        def work():
            try:
                update = lambda message: update_job(key, message=message)
                cancel = signals[key].is_set
                if action == 'prepare':
                    import tempfile
                    with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
                        uploads = {'images': [io.BytesIO(base64.b64decode(value, validate=True)) for value in data.pop('images')]}
                        for name in ('narration', 'music'):
                            if data.get(name):
                                path = Path(temporary) / (name + '.audio')
                                path.write_bytes(base64.b64decode(data.pop(name), validate=True))
                                uploads[name] = path
                        result = projects.prepare(data, uploads, update, cancel)
                elif action == 'preview':
                    result = projects.preview(data['project_id'], update, cancel, data.get('scene_index', 0))
                else:
                    result = projects.export(data['project_id'], update, cancel)
                update_job(key, status='done', message='Hoàn tất bước tham chiếu', **result)
            except Cancelled as exc:
                update_job(key, status='cancelled', error=str(exc))
            except Exception as exc:
                update_job(key, status='error', error=str(exc))
            finally:
                with lock:
                    signals.pop(key, None)
        threading.Thread(target=work, daemon=True).start()
        self.reply(202, {'id': key})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=7860)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--no-services', action='store_true')
    args = parser.parse_args()
    load_history()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    if not args.no_services:
        threading.Thread(target=start_services, daemon=True).start()
    print(f'Local Affiliate Studio đang chạy trên máy, port {args.port}. Ctrl+C để dừng.', flush=True)
    if not args.no_browser:
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        for signal in list(signals.values()):
            signal.set()
    finally:
        for signal in list(signals.values()):
            signal.set()
        stop_processes()
        server.server_close()
