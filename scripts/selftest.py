"""Render a real 20-second video. --full requires installed GPU AI components."""
import argparse
import io
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from localstudio.engine import ROOT, ffmpeg, render
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--mode', choices=['wan', 'sdxl'], default='wan')
    args = parser.parse_args()
    # A clearly marked demo asset, not a claim about a real product.
    image = Image.new('RGB', (600, 800), '#192a45')
    ImageDraw.Draw(image).rounded_rectangle((180, 130, 420, 680), radius=45, fill='#c6d9ea', outline='#ffffff', width=8)
    blob = io.BytesIO()
    image.save(blob, 'PNG')
    blob.seek(0)
    result = render({'product': 'Sản phẩm minh họa kiểm thử', 'prompt': 'A minimal studio tabletop with warm soft lighting and gentle camera movement. This is a demo, not a real product advertisement.', 'features': 'Đây là video minh họa để kiểm tra phần mềm.', 'duration': 20, 'mode': args.mode if args.full else 'photos', 'use_ollama': args.full, 'speech': 'piper' if args.full else 'espeak', 'quality': 'draft', 'auto_music': True, 'product_overlay': True}, {'images': [blob]}, lambda message: print(message, flush=True))
    video = ROOT / result['video'].lstrip('/')
    # Decode the ENTIRE output; an existing file or open port isn't enough.
    subprocess.run([ffmpeg(), '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
    story = json.loads((ROOT / result['storyboard'].lstrip('/')).read_text(encoding='utf-8'))
    assert sum(story['scene_frames']) == 480
    report = {'full_ai': args.full, 'mode': args.mode if args.full else 'photos', 'decoded': True, 'expected_seconds': 20, 'result': result}
    target = ROOT / 'work' / ('ai-selftest-report.json' if args.full else 'selftest-report.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS:', video, flush=True)
    print('Report:', target, flush=True)


if __name__ == '__main__':
    main()
