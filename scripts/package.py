"""Package source and demo only. Never include user data, weights or environments."""
import hashlib
from pathlib import Path
import zipfile
ROOT = Path(__file__).resolve().parents[1]
TOP = ['app.py', 'README.md', 'LICENSE', '.gitignore', 'requirements.txt', 'requirements-dev.txt', 'setup-windows.bat', 'start-windows.bat', 'test-ai-windows.bat']
DIRS = ['localstudio', 'web', 'scripts', 'tests', 'docs', 'examples']
paths = [ROOT / name for name in TOP]
for directory in DIRS:
    paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.log'))
output = ROOT / 'dist' / 'LocalAffiliateStudio-Windows.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(paths):
        data = path.read_bytes()
        if path.suffix in ('.bat', '.ps1'):
            data = data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        archive.writestr('LocalAffiliateStudio/' + path.relative_to(ROOT).as_posix(), data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert not any('/.venv/' in name or '/runtime/' in name or '/work/' in name or '/outputs/' in name or '/models/' in name for name in archive.namelist())
checksum = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix('.zip.sha256').write_text(checksum + '  ' + output.name + '\n')
print(output)
print(f'{output.stat().st_size:,} bytes; {len(paths)} files; SHA256 {checksum}')
