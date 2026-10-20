"""Optional local MuseTalk adapter. No cloud fallback and no silent audio-only mux."""
import json
import os
from pathlib import Path
import shutil
import uuid
from localstudio.paths import ROOT, RUNTIME
from localstudio.process import execute


def configuration():
    path = ROOT / 'lipsync.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    directory = Path(data.get('directory') or RUNTIME / 'MuseTalk').resolve()
    python = Path(data.get('python') or directory / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')).resolve()
    return directory, python


def status():
    try:
        directory, python = configuration()
        required = ['scripts/inference.py', 'models/musetalkV15/musetalk.json', 'models/musetalkV15/unet.pth', 'models/whisper/config.json', 'models/whisper/pytorch_model.bin', 'models/whisper/preprocessor_config.json', 'models/sd-vae/config.json', 'models/sd-vae/diffusion_pytorch_model.bin', 'models/dwpose/dw-ll_ucoco_384.pth', 'models/face-parse-bisent/79999_iter.pth', 'models/face-parse-bisent/resnet18-5c106cde.pth']
        missing = [item for item in required if not (directory / item).is_file()]
        if not python.is_file():
            missing.append('Python environment')
        return {'configured': not missing, 'backend': 'MuseTalk v1.5 local', 'missing': missing, 'inference_verified': False}
    except Exception as exc:
        return {'configured': False, 'error': str(exc), 'inference_verified': False}


def require_available():
    state = status()
    if not state['configured']:
        raise ValueError('Prompt yêu cầu khớp môi nhưng MuseTalk local chưa được cấu hình đủ. Xem docs/REFERENCE.md. Không xuất video voiceover giả làm lip-sync. Có thể chủ động chọn voiceover để đổi yêu cầu; ứng dụng không tự đổi.')


def apply(video, audio, output, cancel=None):
    require_available()
    from localstudio.engine import ffmpeg, run
    directory, python = configuration()
    # Upstream invokes FFmpeg via shell; use ONLY generated relative ASCII paths,
    # never filenames/commands supplied by a browser or product prompt.
    session = directory / 'studio_runs' / uuid.uuid4().hex
    session.mkdir(parents=True)
    shutil.copy2(video, session / 'video.mp4')
    shutil.copy2(audio, session / 'audio.wav')
    relative = session.relative_to(directory).as_posix()
    config = {'studio': {'video_path': relative + '/video.mp4', 'audio_path': relative + '/audio.wav'}}
    (session / 'input.json').write_text(json.dumps(config), encoding='utf-8')  # JSON is valid YAML/OmegaConf.
    environment = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1'}
    command = [str(python), '-m', 'scripts.inference', '--inference_config', relative + '/input.json', '--version', 'v15', '--unet_config', 'models/musetalkV15/musetalk.json', '--unet_model_path', 'models/musetalkV15/unet.pth', '--result_dir', relative + '/results', '--output_vid_name', 'synced.mp4', '--batch_size', '2', '--use_float16', '--ffmpeg_path', str(RUNTIME / 'ffmpeg-bin')]
    # Give this child environment the FFmpeg PATH; do not mutate server env/cwd.
    env = os.environ.copy()
    env.update(environment)
    ffmpeg_bin = RUNTIME / 'ffmpeg-bin'
    ffmpeg_bin.mkdir(parents=True, exist_ok=True)
    named_ffmpeg = ffmpeg_bin / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    if not named_ffmpeg.exists():
        shutil.copy2(ffmpeg(), named_ffmpeg)
    env['PATH'] = str(ffmpeg_bin) + os.pathsep + env.get('PATH', '')
    execute(command, cwd=directory, cancel=cancel, timeout=3600, env=env)
    result = session / 'results/v15/synced.mp4'
    if not result.is_file() or result.stat().st_size < 1000:
        raise RuntimeError('MuseTalk không tạo output. Có thể không tìm được khuôn mặt hoặc thiếu dependency; không tự bỏ qua lip-sync.')
    run(['-i', str(result), '-f', 'null', '-'], cancel)
    shutil.copy2(result, output)
