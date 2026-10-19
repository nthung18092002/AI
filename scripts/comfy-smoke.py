"""Check real ComfyUI core nodes and WEBM transport WITHOUT claiming AI inference."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from localstudio.engine import comfy_generate, ffmpeg, request_json
from localstudio.paths import ROOT
from localstudio.workflows import wan_workflow, sdxl_workflow, validate_graph

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8188')
args = parser.parse_args()
base = args.url.rstrip('/')
info = request_json(base + '/object_info', timeout=60)
checks = []
for name, graph in [('wan', wan_workflow()), ('sdxl', sdxl_workflow())]:
    missing = []
    for node in graph.values():
        spec = info[node['class_type']]
        for key, meta in spec.get('input', {}).get('required', {}).items():
            if key not in node['inputs']:
                raise RuntimeError(f'{name}: missing {node["class_type"]}.{key}')
            value = node['inputs'][key]
            if isinstance(meta[0], list) and not isinstance(value, list) and value not in meta[0]:
                if key not in ('unet_name', 'clip_name', 'vae_name', 'ckpt_name'):
                    raise RuntimeError(f'{name}: unsupported {key}={value}')
                missing.append(value)
    checks.append({'workflow': name, 'core_schemas_match': True, 'missing_models': missing})
folder = ROOT / 'work/comfy-core-smoke'
folder.mkdir(parents=True, exist_ok=True)
graph = {'1': {'class_type': 'EmptyImage', 'inputs': {'width': 160, 'height': 288, 'batch_size': 8, 'color': 0x336699}}, '2': {'class_type': 'SaveWEBM', 'inputs': {'images': ['1', 0], 'filename_prefix': 'LocalStudio/{{PROMPT}}', 'codec': 'vp9', 'fps': 16.0, 'crf': 24.0}}}
validate_graph(graph, info)
asset = comfy_generate(graph, 'core-test', base, folder, 0)
subprocess.run([ffmpeg(), '-v', 'error', '-i', str(asset), '-f', 'null', '-'], check=True)
report = {'comfy_version': request_json(base + '/system_stats')['system'].get('comfyui_version'), 'checks': checks, 'core_webm_download_decode': True, 'ai_inference_executed': False}
(ROOT / 'work/comfy-core-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
