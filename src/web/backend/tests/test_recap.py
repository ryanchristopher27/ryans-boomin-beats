"""F3f: Save tonight's set's recap and the playlist description it fills."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError  # noqa: E402

from routers.dj import RecapRequest, TrackRef, clean_recap, recap_prompt  # noqa: E402
from routers.spotify_actions import CreatePlaylistRequest  # noqa: E402


class Recap(unittest.TestCase):
    def test_prompt_lists_the_set_in_order(self):
        p = recap_prompt([TrackRef(title='4EVA', artist='KAYTRANADA'), TrackRef(title='Redbone', artist='Childish Gambino')])
        self.assertIn('1. 4EVA — KAYTRANADA\n2. Redbone — Childish Gambino', p)

    def test_recap_is_one_line_within_spotifys_limit(self):
        self.assertEqual(clean_recap('  "A warm\n night that built\tto a peak."  '), 'A warm night that built to a peak.')
        long = clean_recap('word ' * 100)
        self.assertLessEqual(len(long), 300)
        self.assertTrue(long.endswith('…'))

    def test_request_bounds(self):
        with self.assertRaises(ValidationError):
            RecapRequest(songs=[])
        with self.assertRaises(ValidationError):
            CreatePlaylistRequest(name='x', description='d' * 301)
        with self.assertRaises(ValidationError):
            CreatePlaylistRequest(name='')
        self.assertEqual(CreatePlaylistRequest(name='Tonight').description, '')


if __name__ == '__main__':
    unittest.main()
