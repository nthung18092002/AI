"""Installation diagnostics. Saves a local report without environment secrets."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from localstudio.engine import ffmpeg, request_json
from localstudio.paths import ROOT, COMFY, PIPER_MODEL
from localstudio.services import start_services, stop_children
from localstudio.speech import espeak_speech, piper_speech, wave_seconds
from localstudio.workflows import validate_graph, wan_workflow, sdxl_workflow, reference_frame_workflow, reference_video_workflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=['basic', 'images', 'video', 'all', 'reference'], default='reference')
    parser.add_argument('--verify-models', action='store_true')
    args = parser.parse_args()
    checks = []
    def check(name, action):
        try:
            detail = action()
            checks.append({'name': name, 'passed': True, 'detail': detail})
            print('PASS', name, detail or '', flush=True)
        except Exception as exc:
            checks.append({'name': name, 'passed': False, 'detail': str(exc)})
            print('FAIL', name, str(exc), flush=True)
    def encoder():
        result = subprocess.run([ffmpeg(), '-hide_banner', '-filters'], capture_output=True, text=True, check=True)
        if 'subtitles' not in result.stdout:
            raise RuntimeError('FFmpeg thiếu subtitles/libass.')
        return ffmpeg()
    check('FFmpeg subtitles', encoder)
    with tempfile.TemporaryDirectory() as tmp:
        def voice(provider):
            path = Path(tmp) / (provider + '.wav')
            if provider == 'piper':
                piper_speech('Xin chào, đây là bài kiểm tra lời đọc tiếng Việt.', path, PIPER_MODEL)
            else:
                espeak_speech('Xin chào, đây là bài kiểm tra lời đọc tiếng Việt.', path)
            return {'seconds': wave_seconds(path)}
        check('eSpeak tiếng Việt', lambda: voice('espeak'))
        check('Piper tiếng Việt', lambda: voice('piper'))
    if args.profile != 'basic':
        def cuda():
            python = COMFY / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            result = subprocess.run([str(python), '-c', 'import torch; assert torch.cuda.is_available(), "CUDA not available"; x=torch.ones((32,32),device="cuda"); assert (x@x)[0,0].item()==32; print(torch.cuda.get_device_name(),torch.__version__)'], capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(result.stderr[-2000:])
            return result.stdout.strip()
        check('CUDA thực thi tensor trên GPU', cuda)
        try:
            start_services()
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                try:
                    request_json('http://127.0.0.1:8188/system_stats', timeout=2)
                    request_json('http://127.0.0.1:11434/api/tags', timeout=2)
                    break
                except Exception:
                    time.sleep(2)
            def ollama():
                models = request_json('http://127.0.0.1:11434/api/tags')['models']
                if not any(m['name'] == 'qwen2.5:3b' for m in models):
                    raise RuntimeError('Chưa có qwen2.5:3b. Chạy ollama pull qwen2.5:3b.')
                return 'qwen2.5:3b đã cài; kiểm thử suy luận bằng test-ai-windows.bat'
            check('Ollama model', ollama)
            def graph(profile):
                info = request_json('http://127.0.0.1:8188/object_info', timeout=60)
                if profile == 'reference':
                    from localstudio.comfy_upload import upload_image
                    from PIL import Image
                    import io
                    image = io.BytesIO();Image.new('RGB', (32, 32), 'white').save(image, 'PNG');image.seek(0)
                    name = upload_image('http://127.0.0.1:8188', image)
                    info = request_json('http://127.0.0.1:8188/object_info', timeout=60)
                    validate_graph(reference_frame_workflow(name), info)
                    validate_graph(reference_video_workflow(name), info)
                else:
                    validate_graph(wan_workflow() if profile == 'video' else sdxl_workflow(), info)
                return 'Node schema và tên model khớp ComfyUI; chưa chạy suy luận.'
            for profile in (['video', 'images'] if args.profile == 'all' else [args.profile]):
                check('ComfyUI ' + profile, lambda p=profile: graph(p))
        finally:
            stop_children()
    if args.verify_models:
        def integrity():
            from localstudio.assets import digest
            records = json.loads((ROOT / 'models/download-records.json').read_text())
            for item in records:
                git_blob = item['algorithm'] == 'git-blob-sha1'
                if digest(ROOT / item['local'], 'sha1' if git_blob else 'sha256', git_blob) != item['checksum']:
                    raise RuntimeError('Checksum sai: ' + item['local'])
            if not records:
                raise RuntimeError('Chưa có bản ghi tải model.')
            return f'{len(records)} files verified'
        check('Model integrity', integrity)
    report = ROOT / 'work' / 'doctor-report.json'
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps({'checks': checks, 'passed': all(c['passed'] for c in checks)}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', report)
    return 0 if all(c['passed'] for c in checks) else 1


if __name__ == '__main__':
    sys.exit(main())
