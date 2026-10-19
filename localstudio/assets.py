"""Explicit installation-time downloads, with TLS and content verification."""
import hashlib
import json
import tempfile
from pathlib import Path
import shutil
import urllib.parse
import urllib.request
import zipfile

from localstudio.paths import ROOT, COMFY, PIPER_MODEL

class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise RuntimeError('Từ chối redirect tải model qua kết nối không có TLS.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def https_open(url, timeout=90):
    return urllib.request.build_opener(HTTPSRedirect()).open(url, timeout=timeout)


COMFY_COMMIT = '8f04fd6ecf4a548937971e840af2a985529fab76'
COMFY_ZIP_SHA256 = '5a2331bbdeda600efe919e7bba0e74da80e5a44415a6aa0274aef0fd2a018853'
VOICE_REPO = 'rhasspy/piper-voices'
VOICE_FOLDER = 'vi/vi_VN/vais1000/medium/'
WAN_REPO = 'Comfy-Org/Wan_2.1_ComfyUI_repackaged'


def digest(path, algorithm='sha256', git_blob=False):
    h = hashlib.new(algorithm)
    if git_blob:
        h.update(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as source:
        while chunk := source.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def download_verified(url, destination, expected, algorithm='sha256', git_blob=False):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        if digest(destination, algorithm, git_blob) == expected:
            print('Đã có, checksum đúng:', destination.name, flush=True)
            return
        raise RuntimeError(f'Checksum không khớp: {destination}. Không ghi đè; hãy kiểm tra/xóa file lỗi rồi chạy lại.')
    if not url.startswith('https://'):
        raise ValueError('Tải model chỉ qua HTTPS có xác minh TLS.')
    temporary = destination.with_name(destination.name + '.partial')
    try:
        print('Đang tải:', destination.name, flush=True)
        with https_open(url, timeout=90) as response, temporary.open('wb') as output:
            if urllib.parse.urlsplit(response.url).scheme != 'https':
                raise RuntimeError('Từ chối tải qua kết nối không có TLS.')
            total = int(response.headers.get('Content-Length') or 0)
            done, milestone = 0, 0
            while chunk := response.read(4 * 1024 * 1024):
                output.write(chunk)
                done += len(chunk)
                if done >= milestone:
                    print(f'  {done//1048576} MB' + (f' / {total//1048576} MB' if total else ''), flush=True)
                    milestone = done + 256 * 1024 * 1024
        if digest(temporary, algorithm, git_blob) != expected:
            raise RuntimeError('Checksum tải về sai: ' + destination.name)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def hf_manifest(repo):
    url = 'https://huggingface.co/api/models/' + repo + '?blobs=true'
    with https_open(url, timeout=45) as response:
        meta = json.load(response)
    if not meta.get('sha'):
        raise RuntimeError('Hugging Face không trả revision cho ' + repo)
    return meta


def hf_files(repo, wanted):
    """Resolve once to an immutable revision. Verify LFS SHA256 or Git blob SHA1."""
    meta = hf_manifest(repo)
    records = {entry['rfilename']: entry for entry in meta['siblings']}
    lockpath = ROOT / 'models' / 'download-records.json'
    lockpath.parent.mkdir(exist_ok=True)
    lock = json.loads(lockpath.read_text(encoding='utf-8')) if lockpath.is_file() else []
    for remote, local in wanted:
        if remote not in records:
            raise RuntimeError(f'Không tìm thấy file chính thức {repo}/{remote}')
        entry = records[remote]
        lfs = entry.get('lfs')
        checksum = lfs['sha256'] if lfs else entry.get('blobId')
        if not checksum:
            raise RuntimeError('Nguồn không cung cấp checksum: ' + remote)
        url = f'https://huggingface.co/{repo}/resolve/{meta["sha"]}/' + urllib.parse.quote(remote, safe='/')
        download_verified(url, local, checksum, 'sha256' if lfs else 'sha1', git_blob=not lfs)
        lock = [item for item in lock if item['local'] != str(Path(local).relative_to(ROOT))]
        lock.append({'repo': repo, 'revision': meta['sha'], 'file': remote, 'local': str(Path(local).relative_to(ROOT)), 'checksum': checksum, 'algorithm': 'sha256' if lfs else 'git-blob-sha1'})
        lockpath.write_text(json.dumps(lock, indent=2), encoding='utf-8')


def install_voice():
    hf_files(VOICE_REPO, [
        (VOICE_FOLDER + PIPER_MODEL.name, PIPER_MODEL),
        (VOICE_FOLDER + PIPER_MODEL.name + '.json', Path(str(PIPER_MODEL) + '.json')),
        (VOICE_FOLDER + 'MODEL_CARD', PIPER_MODEL.parent / 'MODEL_CARD'),
    ])


def install_visuals(profile):
    from localstudio.workflows import WAN_FILES, SDXL_FILE
    if profile in ('video', 'all'):
        targets = [
            ('split_files/diffusion_models/' + WAN_FILES['unet'], COMFY / 'models/diffusion_models' / WAN_FILES['unet']),
            ('split_files/text_encoders/' + WAN_FILES['clip'], COMFY / 'models/text_encoders' / WAN_FILES['clip']),
            ('split_files/vae/' + WAN_FILES['vae'], COMFY / 'models/vae' / WAN_FILES['vae']),
        ]
        hf_files(WAN_REPO, targets)
    if profile in ('images', 'all'):
        hf_files('stabilityai/stable-diffusion-xl-base-1.0', [(SDXL_FILE, COMFY / 'models/checkpoints' / SDXL_FILE)])


def install_comfy_source():
    marker = COMFY / '.studio-source'
    if COMFY.exists():
        if marker.is_file() and marker.read_text().strip() == COMFY_COMMIT:
            return
        raise RuntimeError(f'{COMFY} đã tồn tại và không do bộ cài này quản lý. Không ghi đè dữ liệu cũ.')
    archive = ROOT / 'work' / 'downloads' / 'comfyui.zip'
    download_verified('https://codeload.github.com/Comfy-Org/ComfyUI/zip/' + COMFY_COMMIT, archive, COMFY_ZIP_SHA256)
    COMFY.parent.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='comfy-stage-', dir=COMFY.parent))
    try:
        _extract_source(archive, stage)
        (stage / '.studio-source').write_text(COMFY_COMMIT)
        stage.rename(COMFY)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _extract_source(archive, destination):
    with zipfile.ZipFile(archive) as source:
        top = f'ComfyUI-{COMFY_COMMIT}/'
        for entry in source.infolist():
            if not entry.filename.startswith(top):
                raise ValueError('Archive ComfyUI không đúng cấu trúc.')
            relative = Path(entry.filename[len(top):])
            if '..' in relative.parts or relative.is_absolute():
                raise ValueError('Archive có đường dẫn không hợp lệ.')
            path = destination / relative
            if entry.is_dir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with source.open(entry) as src, path.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
