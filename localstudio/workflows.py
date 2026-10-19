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
