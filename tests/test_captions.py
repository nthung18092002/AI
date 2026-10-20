import unittest
from localstudio.engine import caption_cues


class CaptionTests(unittest.TestCase):
    def test_long_narration_is_split_without_losing_words(self):
        text = 'Trong bếp nhà mình có một món luôn để trong tầm tay đó là khăn giấy dùng để lau bàn và giữ góc bếp gọn gàng mỗi ngày.'
        cues = caption_cues(text, 3, 12, 7)
        self.assertGreater(len(cues), 1)
        displayed = []
        for cue in cues:
            lines = cue.strip().splitlines()
            self.assertLessEqual(len(lines[2:]), 2)
            displayed.extend(' '.join(lines[2:]).split())
        self.assertEqual(displayed, text.split())
        self.assertTrue(cues[0].startswith('7\n00:00:03,000'))
        self.assertIn('00:00:12,000', cues[-1])
