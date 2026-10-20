import io
import json
import uuid
import urllib.request
from pathlib import PurePosixPath
from PIL import Image, ImageOps
from localstudio.network import open_local


def upload_image(base, source):
    """Upload actual pixels to ComfyUI's input store, not a prompt-only filename."""
    with Image.open(source) as image:
        if image.width * image.height > 25_000_000:
            raise ValueError('Ảnh tối đa 25 megapixel.')
        buffer = io.BytesIO()
        ImageOps.exif_transpose(image).convert('RGB').save(buffer, format='PNG')
    boundary = 'Studio' + uuid.uuid4().hex
    filename = uuid.uuid4().hex + '.png'
    content = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode() + buffer.getvalue() + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\ninput\r\n--{boundary}--\r\n'.encode())
    request = urllib.request.Request(base.rstrip('/') + '/upload/image', data=content, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with open_local(request, timeout=60) as response:
        result = json.load(response)
    path = PurePosixPath(result.get('subfolder') or '') / result['name']
    if path.is_absolute() or '..' in path.parts or '\\' in str(path):
        raise ValueError('ComfyUI trả về đường dẫn ảnh không hợp lệ.')
    return str(path)
