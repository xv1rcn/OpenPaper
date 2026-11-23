import tempfile
import unittest
from unittest.mock import patch
from backend.quick_reading.storage import get_speedread_cache
from backend.quick_reading.prompts import build_speedread_prompt

class ReadingFeedbackTests(unittest.TestCase):
    def test_missing_cache_has_explicit_code_but_io_error_remains_error(self):
        with tempfile.TemporaryDirectory() as root:
            result = get_speedread_cache('paper.pdf', root, '.cache')
            self.assertEqual(result.status, 404)
            self.assertEqual(result.payload['code'], 'speedread_not_generated')
            with patch('backend.quick_reading.storage.load_speedread_cache', side_effect=OSError('disk error')):
                failure = get_speedread_cache('paper.pdf', root, '.cache')
            self.assertEqual(failure.status, 500)
            self.assertNotIn('code', failure.payload)

    def test_brief_prompt_does_not_contradict_its_length_goal(self):
        prompt = build_speedread_prompt({}, 'Synthetic evidence', [], {'depth': 'brief', 'include_figure_insights': False})
        self.assertIn('600-900', prompt)
        self.assertNotIn('实验速读必须详细', prompt)
        self.assertIn('事实、证据与关键局限优先', prompt)
