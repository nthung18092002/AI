from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / 'models'
RUNTIME = ROOT / 'runtime'
PIPER_MODEL = MODELS / 'piper' / 'vi_VN-vais1000-medium.onnx'
COMFY = RUNTIME / 'ComfyUI'
