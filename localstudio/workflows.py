"""Built-in ComfyUI graphs: only core nodes, no cloud/custom-node dependency."""
import secrets

WAN_FILES = {
    'unet': 'wan2.1_t2v_1.3B_fp16.safetensors',
    'clip': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors',
    'vae': 'wan_2.1_vae.safetensors',
}
SDXL_FILE = 'sd_xl_base_1.0.safetensors'


def wan_workflow(quality='balanced'):
    width, height, frames, steps = (288, 512, 49, 16) if quality == 'draft' else (480, 832, 81, 24)
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': WAN_FILES['unet'], 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': WAN_FILES['clip'], 'type': 'wan', 'device': 'cpu'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': WAN_FILES['vae']}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{PROMPT}}', 'clip': ['2', 0]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'blurry, low quality, text, subtitles, watermark, logo, distorted objects, deformed hands, static, flicker', 'clip': ['2', 0]}},
        '6': {'class_type': 'EmptyHunyuanLatentVideo', 'inputs': {'width': width, 'height': height, 'length': frames, 'batch_size': 1}},
        '7': {'class_type': 'ModelSamplingSD3', 'inputs': {'model': ['1', 0], 'shift': 8.0}},
        '8': {'class_type': 'KSampler', 'inputs': {'model': ['7', 0], 'seed': secrets.randbelow(2**53), 'steps': steps, 'cfg': 6.0, 'sampler_name': 'uni_pc', 'scheduler': 'simple', 'positive': ['4', 0], 'negative': ['5', 0], 'latent_image': ['6', 0], 'denoise': 1.0}},
        '9': {'class_type': 'VAEDecodeTiled', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0], 'tile_size': 256, 'overlap': 64, 'temporal_size': 16, 'temporal_overlap': 4}},
        '10': {'class_type': 'SaveWEBM', 'inputs': {'images': ['9', 0], 'filename_prefix': 'LocalStudio/scene', 'codec': 'vp9', 'fps': 16.0, 'crf': 24.0}},
    }


def sdxl_workflow(quality='balanced'):
    width, height, steps = (576, 1024, 16) if quality == 'draft' else (768, 1344, 25)
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': SDXL_FILE}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{PROMPT}}', 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'text, watermark, blurry, low quality, distorted objects', 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
        '5': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'seed': secrets.randbelow(2**53), 'steps': steps, 'cfg': 6.0, 'sampler_name': 'dpmpp_2m', 'scheduler': 'karras', 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0], 'denoise': 1.0}},
        '6': {'class_type': 'VAEDecodeTiled', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2], 'tile_size': 512, 'overlap': 64, 'temporal_size': 16, 'temporal_overlap': 4}},
        '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'LocalStudio/image'}},
    }


def validate_graph(graph, info):
    """Validate against this installed ComfyUI version, not assumed schemas."""
    problems = []
    for node in graph.values():
        name = node['class_type']
        if name not in info:
            problems.append('Thiếu node ' + name)
            continue
        required = info[name].get('input', {}).get('required', {})
        for key, spec in required.items():
            if key not in node['inputs']:
                problems.append(f'{name}: thiếu input {key}')
                continue
            value = node['inputs'][key]
            if isinstance(spec, list) and spec and isinstance(spec[0], list) and not isinstance(value, list) and value not in spec[0]:
                problems.append(f'{name}: chưa có model/tùy chọn {value}')
    if problems:
        raise ValueError('ComfyUI chưa sẵn sàng: ' + '; '.join(problems))


REFERENCE_FILES = {
    'editor': 'flux-2-klein-4b-fp8.safetensors',
    'editor_clip': 'qwen_3_4b.safetensors',
    'editor_vae': 'flux2-vae.safetensors',
    'video': 'wan2.2_ti2v_5B_fp16.safetensors',
    'video_vae': 'wan2.2_vae.safetensors',
}


def reference_frame_workflow(product_image, anchor_image=None, seed=0):
    """Image bytes -> VAE -> ReferenceLatent. No overlay or T2V substitute."""
    graph = {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': REFERENCE_FILES['editor'], 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': REFERENCE_FILES['editor_clip'], 'type': 'flux2', 'device': 'cpu'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': REFERENCE_FILES['editor_vae']}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{PROMPT}}', 'clip': ['2', 0]}},
        '5': {'class_type': 'ConditioningZeroOut', 'inputs': {'conditioning': ['4', 0]}},
        '6': {'class_type': 'LoadImage', 'inputs': {'image': product_image}},
        '7': {'class_type': 'ImageScaleToTotalPixels', 'inputs': {'image': ['6', 0], 'upscale_method': 'lanczos', 'megapixels': 0.6, 'resolution_steps': 1}},
        '8': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['7', 0], 'vae': ['3', 0]}},
        '9': {'class_type': 'ReferenceLatent', 'inputs': {'conditioning': ['4', 0], 'latent': ['8', 0]}},
        '10': {'class_type': 'ReferenceLatent', 'inputs': {'conditioning': ['5', 0], 'latent': ['8', 0]}},
        '11': {'class_type': 'EmptyFlux2LatentImage', 'inputs': {'width': 576, 'height': 1024, 'batch_size': 1}},
        '12': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': seed}},
        '13': {'class_type': 'KSamplerSelect', 'inputs': {'sampler_name': 'euler'}},
        '14': {'class_type': 'Flux2Scheduler', 'inputs': {'steps': 4, 'width': 576, 'height': 1024}},
        '15': {'class_type': 'CFGGuider', 'inputs': {'model': ['1', 0], 'positive': ['9', 0], 'negative': ['10', 0], 'cfg': 1.0}},
        '16': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'noise': ['12', 0], 'guider': ['15', 0], 'sampler': ['13', 0], 'sigmas': ['14', 0], 'latent_image': ['11', 0]}},
        '17': {'class_type': 'VAEDecodeTiled', 'inputs': {'samples': ['16', 0], 'vae': ['3', 0], 'tile_size': 256, 'overlap': 64, 'temporal_size': 16, 'temporal_overlap': 4}},
        '18': {'class_type': 'SaveImage', 'inputs': {'images': ['17', 0], 'filename_prefix': 'LocalStudio/reference'}},
    }
    if anchor_image:
        graph.update({
            '20': {'class_type': 'LoadImage', 'inputs': {'image': anchor_image}},
            '21': {'class_type': 'ImageScaleToTotalPixels', 'inputs': {'image': ['20', 0], 'upscale_method': 'lanczos', 'megapixels': 0.6, 'resolution_steps': 1}},
            '22': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['21', 0], 'vae': ['3', 0]}},
            '23': {'class_type': 'ReferenceLatent', 'inputs': {'conditioning': ['9', 0], 'latent': ['22', 0]}},
            '24': {'class_type': 'ReferenceLatent', 'inputs': {'conditioning': ['10', 0], 'latent': ['22', 0]}},
        })
        graph['15']['inputs'].update(positive=['23', 0], negative=['24', 0])
    return graph


def reference_video_workflow(start_image, frames=73, quality='balanced', seed=0):
    """Wan 2.2 TI2V 5B. Uses its dedicated VAE/48-channel reference latent."""
    width, height, steps = (288, 512, 16) if quality == 'draft' else (576, 1024, 24)
    if not 5 <= frames <= 121 or frames % 4 != 1:
        raise ValueError('I2V chunk length must be 4n+1, from 5 to 121 frames.')
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': REFERENCE_FILES['video'], 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': WAN_FILES['clip'], 'type': 'wan', 'device': 'cpu'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': REFERENCE_FILES['video_vae']}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{PROMPT}}', 'clip': ['2', 0]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'deformed hands, extra fingers, face morphing, different person, altered packaging, changed logo, warped letters, subtitles, added text, watermark, extra people, abrupt cuts, flicker', 'clip': ['2', 0]}},
        '6': {'class_type': 'LoadImage', 'inputs': {'image': start_image}},
        '7': {'class_type': 'Wan22ImageToVideoLatent', 'inputs': {'vae': ['3', 0], 'width': width, 'height': height, 'length': frames, 'batch_size': 1, 'start_image': ['6', 0]}},
        '8': {'class_type': 'ModelSamplingSD3', 'inputs': {'model': ['1', 0], 'shift': 8.0}},
        '9': {'class_type': 'KSampler', 'inputs': {'model': ['8', 0], 'seed': seed, 'steps': steps, 'cfg': 5.0, 'sampler_name': 'uni_pc', 'scheduler': 'simple', 'positive': ['4', 0], 'negative': ['5', 0], 'latent_image': ['7', 0], 'denoise': 1.0}},
        '10': {'class_type': 'VAEDecodeTiled', 'inputs': {'samples': ['9', 0], 'vae': ['3', 0], 'tile_size': 256, 'overlap': 64, 'temporal_size': 16, 'temporal_overlap': 4}},
        '11': {'class_type': 'SaveWEBM', 'inputs': {'images': ['10', 0], 'filename_prefix': 'LocalStudio/i2v', 'codec': 'vp9', 'fps': 24.0, 'crf': 20.0}},
    }
