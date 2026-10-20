import io
import json
import subprocess
import unittest
from PIL import Image
from localstudio.engine import ROOT, plan, render


class RenderTests(unittest.TestCase):
    def test_invalid_duration(self):
        with self.assertRaises(ValueError):
            plan({'product': 'Đèn', 'prompt': 'Bàn học', 'duration': 19})

    def test_end_to_end(self):
        picture = io.BytesIO()
        Image.new('RGB', (320, 240), '#d99d42').save(picture, format='PNG')
        picture.seek(0)
        # Generated tone verifies the narration and music muxing paths without external voices.
        audio = ROOT / 'work' / 'test-tone.wav'
        audio.parent.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', str(audio)], check=True)
        result = render({'product': 'Đèn bàn', 'prompt': 'Bàn làm việc', 'duration': 20, 'features': 'Ánh sáng ấm\nThiết kế nhỏ gọn'}, {'images': [picture], 'narration': audio, 'music': audio}, lambda _: None, width=180, height=320)
        video = ROOT / result['video'].lstrip('/')
        p = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(video)], capture_output=True, text=True, check=True)
        meta = json.loads(p.stdout)
        self.assertAlmostEqual(float(meta['format']['duration']), 20, delta=.1)
        self.assertEqual({s['codec_type'] for s in meta['streams']}, {'video', 'audio'})
        v = next(s for s in meta['streams'] if s['codec_type'] == 'video')
        self.assertEqual((v['width'], v['height']), (180, 320))
        subtitles = (ROOT / result['subtitles'].lstrip('/')).read_text(encoding='utf-8')
        self.assertIn('Đèn bàn', subtitles)
        self.assertIn('00:00:20,000', subtitles)
        self.assertTrue((ROOT / result['storyboard'].lstrip('/')).is_file())


if __name__ == '__main__':
    unittest.main()
