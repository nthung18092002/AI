import atexit
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import time

from localstudio.engine import ffmpeg, request_json
from localstudio.paths import ROOT, COMFY, PIPER_MODEL
from localstudio.assets import managed_gguf_installed

CHILDREN = []
LOGS = []


def spawn(command, cwd=None, env=None, name='service'):
    logs = ROOT / 'work' / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    log = (logs / f'{name}.log').open('ab')
    LOGS.append(log)
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, **options)
    CHILDREN.append(process)
    return process


def stop_children():
    for process in CHILDREN:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    for log in LOGS:
        log.close()


atexit.register(stop_children)


def start_services():
    """Start only installed components; never install or download at app startup."""
    environment = os.environ.copy()
    environment.update({'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1', 'OLLAMA_NO_CLOUD': '1', 'OLLAMA_HOST': '127.0.0.1:11434'})
    try:
        request_json('http://127.0.0.1:11434/api/tags', timeout=2)
    except Exception:
        executable = shutil.which('ollama')
        if not executable and os.name == 'nt':
            candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe'
            if candidate.is_file():
                executable = str(candidate)
        if executable:
            spawn([executable, 'serve'], env=environment, name='ollama')
    python = COMFY / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if python.is_file():
        try:
            request_json('http://127.0.0.1:8188/system_stats', timeout=2)
        except Exception:
            command = [str(python), 'main.py', '--listen', '127.0.0.1', '--port', '8188', '--lowvram', '--reserve-vram', '1', '--disable-all-custom-nodes', '--offline', '--cache-none']
            if managed_gguf_installed():
                command += ['--whitelist-custom-nodes', 'ComfyUI-GGUF']
            spawn(command, cwd=COMFY, env=environment, name='comfyui')


def system_status():
    result = {'local_only': True, 'piper': PIPER_MODEL.is_file() and Path(str(PIPER_MODEL) + '.json').is_file(), 'espeak': importlib.util.find_spec('espeakng_loader') is not None}
    try:
        p = subprocess.run([ffmpeg(), '-hide_banner', '-filters'], capture_output=True, text=True, timeout=10)
        result['ffmpeg'] = p.returncode == 0 and 'subtitles' in p.stdout and 'overlay' in p.stdout
    except Exception as exc:
        result['ffmpeg'] = False
        result['ffmpeg_error'] = str(exc)
    for key, url in [('ollama', 'http://127.0.0.1:11434/api/tags'), ('comfy', 'http://127.0.0.1:8188/system_stats')]:
        try:
            data = request_json(url, timeout=3)
            result[key] = True
            if key == 'ollama':
                result['ollama_models'] = [m['name'] for m in data.get('models', [])]
            else:
                result['devices'] = [{k: d.get(k) for k in ('name', 'type', 'vram_total', 'vram_free')} for d in data.get('devices', [])]
        except Exception as exc:
            result[key] = False
            result[key + '_error'] = str(exc)
    from localstudio.lipsync import status as lipsync_status
    result['lipsync'] = lipsync_status()
    result['gguf_loader_installed'] = managed_gguf_installed()
    result['installed_assets'] = []
    for folder in ('diffusion_models', 'text_encoders', 'vae', 'checkpoints'):
        path = COMFY / 'models' / folder
        if path.is_dir():
            result['installed_assets'].extend(p.name for p in path.iterdir() if p.is_file() and p.suffix in ('.safetensors', '.gguf'))
    return result
