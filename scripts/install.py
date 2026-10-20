"""Run with the app venv Python. Installs local models; never asks for API keys."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from localstudio.assets import install_comfy_source, install_visuals, install_voice, install_reference_models
from localstudio.paths import ROOT, COMFY


def call(args, cwd=None):
    print('>', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=['basic', 'images', 'video', 'all', 'reference'], default='reference')
    parser.add_argument('--skip-voice', action='store_true', help='Keep eSpeak only; no neural voice download.')
    parser.add_argument('--cpu', action='store_true', help='ComfyUI CPU development checks; not suitable for production video generation.')
    args = parser.parse_args()
    required = 2 if args.profile == 'basic' else 55 if args.profile == 'reference' else 45 if args.profile == 'all' else 35
    if shutil.disk_usage(ROOT).free < required * 1024**3:
        raise RuntimeError(f'Cần tối thiểu {required} GB dung lượng trống để cài profile {args.profile}.')
    if args.profile != 'basic':
        install_comfy_source()
        executable = COMFY / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not executable.is_file():
            venv.EnvBuilder(with_pip=True).create(executable.parents[1])
        index = 'https://download.pytorch.org/whl/cpu' if args.cpu else 'https://download.pytorch.org/whl/cu128'
        call([executable, '-m', 'pip', 'install', 'torch==2.10.0', 'torchvision==0.25.0', '--index-url', index])
        constraints = ROOT / 'scripts' / 'comfy-constraints.txt'
        call([executable, '-m', 'pip', 'install', '-r', COMFY / 'requirements.txt', '-c', constraints])
        call([executable, '-m', 'pip', 'check'])
        if not args.cpu:
            call([executable, '-c', 'import torch; assert torch.cuda.is_available(), "CUDA unavailable: update NVIDIA driver"; x=torch.ones((32,32),device="cuda"); assert (x@x)[0,0].item()==32; print(torch.cuda.get_device_name(), torch.__version__)'])
        if args.profile == 'reference':
            install_reference_models()
        else:
            install_visuals(args.profile)
        ollama = shutil.which('ollama')
        if not ollama and os.name == 'nt':
            candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Ollama/ollama.exe'
            ollama = str(candidate) if candidate.is_file() else None
        if not ollama:
            raise RuntimeError('Chưa có Ollama. Cài Ollama rồi chạy lại bộ cài; các model đã tải được giữ lại.')
        # Ollama may not be serving yet after first installation.
        from localstudio.engine import request_json
        service = None
        try:
            request_json('http://127.0.0.1:11434/api/tags', timeout=3)
        except Exception:
            environment = os.environ.copy()
            environment.update({'OLLAMA_HOST': '127.0.0.1:11434', 'OLLAMA_NO_CLOUD': '1'})
            service = subprocess.Popen([ollama, 'serve'], env=environment)
            import time
            for _ in range(30):
                try:
                    request_json('http://127.0.0.1:11434/api/tags', timeout=2)
                    break
                except Exception:
                    time.sleep(1)
        try:
            call([ollama, 'pull', 'qwen2.5:3b'])
        finally:
            if service:
                service.terminate()
                service.wait(timeout=10)
    if not args.skip_voice:
        install_voice()
    print('Cài model hình/TTS hoàn tất. Chạy start-windows.bat. Lip-sync cần MuseTalk local cài riêng và kiểm thử; chưa được xác nhận bởi bộ cài này. Xem docs/REFERENCE.md và MODEL_CARD của giọng đọc.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('CÀI ĐẶT CHƯA HOÀN TẤT:', exc, file=sys.stderr)
        sys.exit(1)
