import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.library import playlist_stats, summarize

NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


def item(added, year='2021', artist='A'):
    return {'added_at': added, 'track': {'album': {'release_date': f'{year}-01-01'}, 'artists': [{'name': artist}]}}


class Library(unittest.TestCase):
    def test_summary(self):
        items = [item('2026-10-20T00:00:00Z', '2024', 'Drake'), item('2026-10-02T00:00:00Z', '2015', 'Drake'),
                 item('2026-03-01T00:00:00Z', '1994', 'Nas'), item('2019-05-01T00:00:00Z', '2019')]
        s = summarize(items, total=4, now=NOW)
        self.assertEqual((s['this_month'], s['this_year']), (2, 3))
        self.assertEqual(s['months'][-1], {'month': '2026-10', 'count': 2})
        self.assertEqual(s['months'][0]['month'], '2025-11')
        self.assertEqual(s['oldest'][:10], '2019-05-01')
        self.assertEqual([d['decade'] for d in s['decades']], ['1990s', '2010s', '2020s'])
        self.assertEqual(s['top_artists'][0], {'name': 'Drake', 'count': 2})

    def test_partial_scan_has_no_oldest(self):
        self.assertIsNone(summarize([item('2026-10-20T00:00:00Z')], total=9000, now=NOW)['oldest'])

    def test_playlists(self):
        pls = [{'name': 'Mine', 'owner': {'id': 'me'}, 'items': {'total': 30}, 'collaborative': True},
               {'name': 'Big', 'owner': {'id': 'me'}, 'tracks': {'total': 300}},
               {'name': 'Theirs', 'owner': {'id': 'x'}, 'items': {'total': 999}}, None]
        self.assertEqual(playlist_stats(pls, 'me'), {'count': 3, 'owned': 2, 'songs': 330, 'collaborative': 1, 'biggest': {'name': 'Big', 'songs': 300}})


if __name__ == '__main__':
    unittest.main()
