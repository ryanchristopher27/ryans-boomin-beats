import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.spotify_actions import playlist_tracks_from


def track(i):
    return {'type': 'track', 'id': f'id{i}', 'name': f'Song {i}', 'artists': [{'name': 'A'}], 'album': {'images': []}}


class FakeSpotify:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def _get(self, url, **params):
        self.calls.append((url, params))
        return self.pages[params['offset'] // 50]


class PlaylistTracks(unittest.TestCase):
    def test_reads_new_and_old_entry_shapes_and_skips_local_files(self):
        local = {'type': 'track', 'id': None, 'name': 'Local', 'artists': [], 'album': {}}
        sp = FakeSpotify([{'items': [{'item': track(1)}, {'track': track(2)}, {'item': local}, None, {'item': {'type': 'episode'}}], 'next': None}])
        self.assertEqual([t['id'] for t in playlist_tracks_from(sp, 'abc')], ['id1', 'id2'])
        self.assertEqual(sp.calls[0][0], 'playlists/abc/items')

    def test_pages_until_the_limit(self):
        pages = [{'items': [{'item': track(p * 50 + i)} for i in range(50)], 'next': 'more'} for p in range(4)]
        sp = FakeSpotify(pages)
        self.assertEqual(len(playlist_tracks_from(sp, 'abc', limit=120)), 120)
        self.assertEqual(len(sp.calls), 3)


if __name__ == '__main__':
    unittest.main()
