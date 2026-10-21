"""Reviewed reference-image -> image-to-video projects, entirely local."""
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import subprocess
import shutil
import uuid
from PIL import Image, ImageOps
from localstudio.brief import parse_brief
from localstudio.comfy_upload import upload_image
from localstudio.engine import ffmpeg, atempo, caption_cues, plan, request_json, run, comfy_generate
from localstudio.paths import ROOT, PIPER_MODEL
from localstudio.process import check_cancel
from localstudio.speech import ambient_music, espeak_speech, piper_speech, wave_seconds
from localstudio.workflows import reference_frame_workflow, reference_video_workflow, validate_graph, video_backend, video_fps
from localstudio import lipsync

PROJECTS = ROOT / 'work/projects'



def require_frame_count(path, expected):
    result = subprocess.run([ffmpeg(), '-v', 'error', '-nostats', '-progress', 'pipe:1', '-i', str(path), '-map', '0:v:0', '-an', '-f', 'null', '-'], capture_output=True, text=True, timeout=120)
    counts = re.findall(r'^frame=(\d+)\s*$', result.stdout, re.MULTILINE)
    if result.returncode or not counts or int(counts[-1]) != expected:
        raise RuntimeError(f'Video không đủ/đúng frame: cần {expected}, nhận {counts[-1] if counts else "unknown"}. Không tự kéo dài bằng ảnh đứng hoặc lặp clip.')


def project_folder(project_id):
    if not re.fullmatch('[a-f0-9]{32}', str(project_id)):
        raise ValueError('Mã dự án không hợp lệ.')
    return PROJECTS / project_id


def save(folder, manifest):
    temporary = folder / 'manifest.tmp'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(folder / 'manifest.json')


def read(project_id):
    folder = project_folder(project_id)
    return folder, json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media(project_id, filename):
    return f'/projects/{project_id}/{filename}'


def describe(project_id):
    folder, manifest = read(project_id)
    return {'kind': 'reference', 'project_id': project_id, 'video_backend': video_backend(manifest['data']), 'state': manifest['state'], 'frames_approved': manifest.get('approved_hashes') == [sha(folder / f'frame-{i}.png') for i in range(len(manifest['plan']['timeline']))], 'speech_delivery': manifest['data'].get('speech_delivery', 'as_requested'), 'plan': manifest['plan'], 'warnings': manifest['warnings'], 'frames': [{'index': i, 'sha256': sha(folder / f'frame-{i}.png'), 'image': media(project_id, f'frame-{i}.png'), 'voice': media(project_id, f'voice-{i}.wav') if (folder / f'voice-{i}.wav').is_file() else None, 'dialogue': scene['dialogue'], 'start': scene['start'], 'end': scene['end']} for i, scene in enumerate(manifest['plan']['timeline'])], 'previews': [{'index': i, 'video': media(project_id, f'preview-{i}.mp4'), 'sha256': sha(folder / f'preview-{i}.mp4'), 'approved': manifest.get('motion_hashes', {}).get(str(i)) == sha(folder / f'preview-{i}.mp4')} for i in range(len(manifest['plan']['timeline'])) if (folder / f'preview-{i}.mp4').is_file()], 'lipsync': lipsync.status()}


def frame_prompt(scene, context, has_anchor):
    return (
        'Create ONE photorealistic vertical 9:16 starting frame for a product commercial. '
        'Image 1 is the real product reference: retain its packaging shape, exact printed logo, colors, lettering and artwork; do not invent or redesign a package. '
        + ('Image 2 is the shared identity/set anchor: keep exactly the same adult presenter, face, hair, clothes, kitchen, daylight and camera color palette. ' if has_anchor else '')
        + 'Integrate the physical product naturally in the scene with consistent perspective, scale, shadows, hand contact and occlusion. Never add a floating photo, picture-in-picture panel, collage or poster. '
        'Do not render narration, subtitles, captions, prices or any additional text. Packaging printing is part of the physical product. '
        'This is a STILL starting pose, not a montage or all actions at once. Scene context: '
        + context + '\nStarting pose for this shot: ' + scene['action']
    )


def context_from_prompt(prompt):
    # Exclude quoted speech/timing from the image editor instructions.
    first = re.search(r'(?m)^\s*[–—-]?\s*0\s*[–—-]\s*\d+\s*(?:giây|s)\s*:', prompt)
    context = prompt[:first.start()] if first else prompt
    return context[-6000:]


def prepare(data, uploads, progress, cancel=None):
    if len(uploads.get('images', [])) != 1:
        raise ValueError('Cần ảnh sản phẩm thật để tạo khung tham chiếu. Không thay bằng text-to-video.')
    backend = video_backend(data)
    data = {**data, 'video_backend': backend}
    storyboard = plan({**data, 'mode': 'reference'})
    if not storyboard.get('timeline'):
        step = storyboard['duration'] / len(storyboard['lines'])
        storyboard['timeline'] = [{'start': i * step, 'end': (i + 1) * step, 'dialogue': line, 'action': storyboard['visuals'][i]} for i, line in enumerate(storyboard['lines'])]
        parsed = parse_brief(data['prompt'])
        storyboard.update(burn_subtitles=parsed['burn_subtitles'], requires_lipsync=parsed['requires_lipsync'])
    # User can explicitly opt into voiceover, but it is never an automatic fallback.
    storyboard['requested_lipsync'] = storyboard.get('requires_lipsync', False)
    if data.get('speech_delivery') == 'voiceover':
        storyboard['requires_lipsync'] = False
    if 'burn_subtitles' in data:
        storyboard['burn_subtitles'] = bool(data['burn_subtitles']) and storyboard.get('burn_subtitles', True)
    base = str(data.get('comfy_url') or 'http://127.0.0.1:8188').rstrip('/')
    project_id = uuid.uuid4().hex
    folder = project_folder(project_id)
    folder.mkdir(parents=True)
    product = folder / 'product.png'
    with Image.open(uploads['images'][0]) as image:
        if image.width * image.height > 25_000_000:
            raise ValueError('Ảnh tối đa 25 megapixel.')
        ImageOps.exif_transpose(image).convert('RGB').save(product)
    seed = int(data['seed']) if data.get('seed') not in (None, '') else secrets.randbelow(2**53)
    manifest = {'id': project_id, 'state': 'preparing', 'data': {k: v for k, v in data.items() if k not in ('images', 'narration', 'music')}, 'plan': storyboard, 'seed': seed, 'warnings': ['Ảnh có điều kiện giảm drift nhưng không bảo đảm nguyên vẹn mọi logo, chữ hoặc bàn tay. Cần kiểm tra khung và clip thử.', 'Chưa kiểm chứng suy luận/VRAM trên RTX 5070 12GB trong môi trường cloud này.'], 'approved_hashes': None, 'motion_hashes': {}, 'conditioning': []}
    if backend == 'wan22_a14b':
        manifest['warnings'].append('Wan2.2 A14B Q4: hai expert khoảng 17.5GB trọng số, chưa tính text encoder và bộ nhớ chạy. RAM 32GB có thể thiếu; offload sẽ chậm. Chưa đo chất lượng/VRAM trên máy bạn.')
    if storyboard.get('requires_lipsync') and not lipsync.status()['configured']:
        manifest['warnings'].append('Yêu cầu khớp môi đang giữ nguyên. Thiếu MuseTalk local sẽ chặn dựng toàn bộ, không xuất voiceover thay thế.')
    save(folder, manifest)
    for name in ('narration', 'music'):
        if uploads.get(name):
            shutil.copy2(uploads[name], folder / (name + '.audio'))
    for i, scene in enumerate(storyboard['timeline']):
        check_cancel(cancel)
        progress(f'Đang chuẩn bị lời đọc nguyên văn cảnh {i+1}')
        voice = folder / f'voice-{i}.wav'
        duration = scene['end'] - scene['start']
        if (folder / 'narration.audio').is_file():
            run(['-ss', str(scene['start']), '-i', str(folder / 'narration.audio'), '-t', str(duration), '-ar', '24000', '-ac', '1', str(voice)], cancel)
        else:
            provider = data.get('speech') or 'piper'
            raw = folder / f'raw-voice-{i}.wav'
            if provider == 'piper':
                piper_speech(scene['dialogue'], raw, PIPER_MODEL)
            elif provider == 'espeak':
                espeak_speech(scene['dialogue'], raw)
            elif provider == 'none':
                if storyboard.get('requires_lipsync'):
                    raise ValueError('Khớp môi cần lời đọc. Chọn Piper/eSpeak hoặc cung cấp file lời đọc.')
                continue
            else:
                from localstudio.engine import speech_windows
                speech_windows(scene['dialogue'], raw, data.get('voice', ''), cancel)
            ratio = max(1, wave_seconds(raw) / max(.1, duration - .1))
            if ratio > 1.35:
                raise ValueError(f'Lời thoại cảnh {i+1} quá dài cho {duration:g}s với giọng đang chọn. Không tự cắt hoặc tăng tốc quá mức; sửa timeline/giọng rồi thử lại.')
            run(['-i', str(raw), '-af', atempo(ratio) + ',apad', '-t', str(duration), '-ar', '24000', '-ac', '1', str(voice)], cancel)
    progress('Đang đưa ảnh sản phẩm thật vào ComfyUI')
    product_name = upload_image(base, product)
    info = request_json(base + '/object_info', timeout=60)
    # Check BOTH the editor and video model before expensive synthesis.
    validate_graph(reference_frame_workflow(product_name), info)
    validate_graph(reference_video_workflow(product_name, backend=backend), info)
    anchor_name = None
    context = str(data.get('reference_context') or context_from_prompt(data['prompt']))
    for i, scene in enumerate(storyboard['timeline']):
        check_cancel(cancel)
        progress(f'Đang tạo khung tham chiếu {i+1}/{len(storyboard["timeline"])} từ ảnh sản phẩm' + (' và nhân vật/bối cảnh khung đầu' if i else ''))
        graph = reference_frame_workflow(product_name, anchor_name, (seed + i) % 2**53)
        prompt = frame_prompt(scene, context, anchor_name is not None)
        manifest['conditioning'].append({'scene': i, 'product_sha256': sha(product), 'anchor_sha256': sha(folder / 'frame-0.png') if i else None, 'prompt': prompt})
        asset = comfy_generate(graph, prompt, base, folder, i, cancel)
        with Image.open(asset) as image:
            image.convert('RGB').save(folder / f'frame-{i}.png')
        if i == 0:
            anchor_name = upload_image(base, folder / 'frame-0.png')

        save(folder, manifest)
    manifest['state'] = 'awaiting_frame_review'
    save(folder, manifest)
    request_json(base + '/free', {'unload_models': True, 'free_memory': True})
    return describe(project_id)


def approve_frames(project_id, hashes):
    folder, manifest = read(project_id)
    expected = [sha(folder / f'frame-{i}.png') for i in range(len(manifest['plan']['timeline']))]
    if hashes != expected:
        raise ValueError('Khung cảnh đã thay đổi hoặc chưa duyệt đủ. Xem lại tất cả khung hiện tại.')
    if manifest.get('approved_hashes') != expected:
        for path in folder.glob('preview-*.mp4'):
            path.unlink()
        manifest['motion_hashes'] = {}
        manifest['preview_frames'] = {}
    manifest.update(state='frames_approved', approved_hashes=expected)
    save(folder, manifest)
    return describe(project_id)


def ensure_approved(folder, manifest):
    expected = [sha(folder / f'frame-{i}.png') for i in range(len(manifest['plan']['timeline']))]
    if manifest.get('approved_hashes') != expected:
        raise ValueError('Cần duyệt khung hiện tại trước khi chạy I2V; không sinh lại người/sản phẩm từ text.')


def chunk_frames(total, limit=72):
    if total < 0 or limit < 1:
        raise ValueError('Số frame không hợp lệ.')
    parts = []
    while total:
        count = min(total, limit)
        parts.append(count)
        total -= count
    return parts


def generate_scene(folder, manifest, index, target_frames, progress, cancel, reuse_preview=False):
    scene = manifest['plan']['timeline'][index]
    base = str(manifest['data'].get('comfy_url') or 'http://127.0.0.1:8188').rstrip('/')
    quality = manifest['data'].get('quality') or 'balanced'
    backend = video_backend(manifest['data'])
    source_fps = video_fps(backend)
    seed = (manifest['seed'] + index) % 2**53
    reference = folder / f'frame-{index}.png'
    clips = []
    prior = False
    if reuse_preview:
        approved = folder / f'preview-{index}.mp4'
        clips.append(approved)
        target_frames -= manifest['preview_frames'][str(index)]
        reference = folder / f'preview-end-{index}.png'
        run(['-sseof', '-1', '-i', str(approved), '-vf', 'reverse', '-frames:v', '1', str(reference)], cancel)
        prior = True
    for j, count in enumerate(chunk_frames(target_frames, 48 if quality == 'draft' else 72)):
        check_cancel(cancel)
        progress(f'Đang chạy I2V cảnh {index+1}, đoạn {j+1}; dùng ảnh đã duyệt' + (' / khung cuối đoạn trước' if j else ''))
        source_sha = sha(reference)
        name = upload_image(base, reference)
        # Include a boundary frame so the next chunk can omit the repeated first frame.
        source_count = math.ceil(count * source_fps / 24)
        needed = source_count + (1 if j or prior else 0)
        length = 4 * math.ceil((needed - 1) / 4) + 1
        graph = reference_video_workflow(name, max(5, length), quality, (seed + j) % 2**53, backend=backend)
        motion = 'Continue the same person, same face, clothing, physical product and kitchen as the starting image. Stable camera, slow restrained natural motion, no new people or text. Do not redesign the package or its printed artwork. Action in this shot: ' + scene['action']
        asset = comfy_generate(graph, motion, base, folder, 1000 + index * 100 + j, cancel)
        if asset.suffix.lower() not in ('.webm', '.mp4'):
            raise RuntimeError('I2V không trả video. Không dùng ảnh tĩnh thay cho video AI.')
        clip = folder / f'chunk-{index}-{j}.mp4'
        start = 1 if j or prior else 0
        # No overlay, loop, tpad or length stretching in this reference path.
        vf = f'trim=start_frame={start}:end_frame={start+source_count},setpts=PTS-STARTPTS,scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24'
        run(['-i', str(asset), '-vf', vf, '-frames:v', str(count), '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', str(clip)], cancel)
        require_frame_count(clip, count)
        clips.append(clip)
        reference = folder / f'continuation-{index}-{j}.png'
        run(['-sseof', '-1', '-i', str(clip), '-vf', 'reverse', '-frames:v', '1', str(reference)], cancel)
        manifest.setdefault('chunks', []).append({'phase': 'continuation' if reuse_preview else 'preview', 'scene': index, 'chunk': j, 'source_frame_sha256': source_sha, 'seed': (seed + j) % 2**53, 'frames': count, 'video_backend': backend, 'source_fps': source_fps, 'source_frames': source_count})
        save(folder, manifest)
    listing = folder / f'chunks-{index}.txt'
    listing.write_text('\n'.join(f"file '{p.name}'" for p in clips))
    output = folder / f'clip-{index}.mp4'
    run(['-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', str(output)], cancel)
    return output


def preview(project_id, progress, cancel=None, scene_index=0):
    folder, manifest = read(project_id)
    ensure_approved(folder, manifest)
    # Visual-only preview does not claim lip-sync. Final export enforces that separately.
    scene_index = int(scene_index)
    if not 0 <= scene_index < len(manifest['plan']['timeline']):
        raise ValueError('Cảnh thử không hợp lệ.')
    scene = manifest['plan']['timeline'][scene_index]
    frames = min(72, round((scene['end'] - scene['start']) * 24))
    clip = generate_scene(folder, manifest, scene_index, frames, progress, cancel)
    shutil.copy2(clip, folder / f'preview-{scene_index}.mp4')
    manifest.setdefault('preview_frames', {})[str(scene_index)] = frames
    manifest.setdefault('motion_hashes', {}).pop(str(scene_index), None)
    manifest.update(state='awaiting_motion_review')
    save(folder, manifest)
    result = describe(project_id)
    result['latest_preview_index'] = scene_index
    result['preview_visual_only'] = True
    return result


def approve_preview(project_id, checksum, scene_index=0):
    folder, manifest = read(project_id)
    ensure_approved(folder, manifest)
    scene_index = int(scene_index)
    if not 0 <= scene_index < len(manifest['plan']['timeline']):
        raise ValueError('Cảnh thử không hợp lệ.')
    if checksum != sha(folder / f'preview-{scene_index}.mp4'):
        raise ValueError('Clip thử đã thay đổi. Xem lại clip hiện tại.')
    manifest.setdefault('motion_hashes', {})[str(scene_index)] = checksum
    manifest['state'] = 'motion_approved' if len(manifest['motion_hashes']) == len(manifest['plan']['timeline']) else 'awaiting_motion_review'
    save(folder, manifest)
    return describe(project_id)


def export(project_id, progress, cancel=None):
    folder, manifest = read(project_id)
    ensure_approved(folder, manifest)
    for i in range(len(manifest['plan']['timeline'])):
        path = folder / f'preview-{i}.mp4'
        if not path.is_file() or manifest.get('motion_hashes', {}).get(str(i)) != sha(path):
            raise ValueError(f'Cần xem và duyệt clip chuyển động ngắn cảnh {i+1} trước khi dựng toàn bộ.')
    lips = manifest['plan'].get('requires_lipsync', False)
    if lips:
        lipsync.require_available()
    base = str(manifest['data'].get('comfy_url') or 'http://127.0.0.1:8188').rstrip('/')
    clips = []
    for i, scene in enumerate(manifest['plan']['timeline']):
        frames = round((scene['end'] - scene['start']) * 24)
        clip = generate_scene(folder, manifest, i, frames, progress, cancel, reuse_preview=True)
        if lips:
            progress(f'Đang đồng bộ môi local cảnh {i+1}')
            request_json(base + '/free', {'unload_models': True, 'free_memory': True})
            synced = folder / f'synced-{i}.mp4'
            lipsync.apply(clip, folder / f'voice-{i}.wav', synced, cancel)
            require_frame_count(synced, frames)
            clip = synced
        muxed = folder / f'muxed-{i}.mp4'
        # Concatenate VIDEO only. AAC priming per scene otherwise shifts lip timing.
        run(['-i', str(clip), '-map', '0:v:0', '-an', '-frames:v', str(frames), '-vf', 'setpts=N/(24*TB),scale=720:1280,setsar=1', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', str(muxed)], cancel)
        clips.append(muxed)
    cues, cursor = [], 1
    for scene in manifest['plan']['timeline']:
        part = caption_cues(scene['dialogue'], scene['start'], scene['end'], cursor)
        cues.extend(part);cursor += len(part)
    (folder / 'captions.srt').write_text('\n'.join(cues), encoding='utf-8')
    listing = folder / 'final-clips.txt'
    listing.write_text('\n'.join(f"file '{clip.name}'" for clip in clips))
    joined = folder / 'joined.mp4'
    run(['-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', str(joined)], cancel)
    music = folder / 'music.audio'
    if not music.is_file() and manifest['data'].get('auto_music'):
        music = folder / 'ambient.wav'
        ambient_music(music, math.ceil(manifest['plan']['duration']))
    args = ['-i', str(joined)]
    voice_files = [folder / f'voice-{i}.wav' for i in range(len(clips))]
    has_voice = all(path.is_file() for path in voice_files)
    if any(path.is_file() for path in voice_files) and not has_voice:
        raise ValueError('Thiếu lời đọc ở một số cảnh; không xuất âm thanh sai timeline.')
    index = 1
    if has_voice:
        voice_list = folder / 'voices.txt'
        voice_list.write_text('\n'.join(f"file '{path.name}'" for path in voice_files))
        narration = folder / 'narration.wav'
        run(['-f', 'concat', '-safe', '0', '-i', str(voice_list), '-c:a', 'pcm_s16le', str(narration)], cancel)
        args += ['-i', str(narration)]
        index += 1
    if music.is_file():
        args += ['-stream_loop', '-1', '-i', str(music)]
        filters = f'[{index}:a]volume=0.12[music]'
        if has_voice:
            filters += ';[1:a][music]amix=inputs=2:duration=first:normalize=0[audio]'
        args += ['-filter_complex', filters, '-map', '0:v:0', '-map', '[audio]' if has_voice else '[music]']
    elif has_voice:
        args += ['-map', '0:v:0', '-map', '1:a:0']
    vf = 'setpts=N/(24*TB)'
    if manifest['plan'].get('burn_subtitles', False):
        vf += ",subtitles=captions.srt:force_style='FontName=Arial,FontSize=13,Outline=1.2,MarginV=28'"
    args += ['-vf', vf]
    require_frame_count(joined, round(manifest['plan']['duration'] * 24))
    output_id = uuid.uuid4().hex
    output = ROOT / 'outputs'
    output.mkdir(exist_ok=True)
    target = output / f'{output_id}.mp4'
    partial = output / f'{output_id}.partial.mp4'
    try:
        run([*args, '-t', str(manifest['plan']['duration']), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(partial)], cancel, cwd=folder)
        check_cancel(cancel)
        require_frame_count(partial, round(manifest['plan']['duration'] * 24))
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    manifest['state'] = 'exported'
    manifest['actual_delivery'] = 'musetalk_lipsync' if lips else 'voiceover' if has_voice else 'silent'
    save(folder, manifest)
    shutil.copy2(folder / 'captions.srt', output / f'{output_id}.srt')
    (output / f'{output_id}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'kind': 'video', 'project_id': project_id, 'video': f'/outputs/{output_id}.mp4', 'subtitles': f'/outputs/{output_id}.srt', 'storyboard': f'/outputs/{output_id}.json'}


def set_delivery(project_id, delivery):
    if delivery not in ('as_requested', 'voiceover'):
        raise ValueError('Chế độ lời đọc không hợp lệ.')
    folder, manifest = read(project_id)
    manifest['data']['speech_delivery'] = delivery
    manifest['plan']['requires_lipsync'] = manifest['plan'].get('requested_lipsync', False) and delivery != 'voiceover'
    save(folder, manifest)
    return describe(project_id)
