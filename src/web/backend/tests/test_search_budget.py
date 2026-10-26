"""Spotify search budget (tracker e2df2d): the DJ validates only what it needs,
the shared Supabase cache short-circuits repeat lookups, and searches are
capped in flight. Spotify and Supabase are faked.

    python -m unittest tests.test_search_budget -v
"""
import asyncio
import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.dj import fill_moves  # noqa: E402
from services import spotify_validator, track_cache  # noqa: E402


def entry(title, artist='A'):
    return {'title': title, 'artist': artist, 'reason': 'r'}


def track(tid, artist='A'):
    return {'id': tid, 'title': tid, 'artists': [artist], 'image': '', 'explicit': False}


class EarlyStop(unittest.TestCase):
    def run_fill(self, moves, known):
        """`known`: title -> Spotify track (missing = no match). Returns (result, titles searched)."""
        searched = []

        async def validate(batch, fallback=True):
            searched.extend(e['title'] for e in batch)
            return [{**e, 'spotify': known[e['title']]} for e in batch if e['title'] in known], []

        result = asyncio.run(fill_moves(moves, set(), 2, validate=validate))
        return result, searched

    def test_looks_up_only_per_move_when_everything_matches(self):
        moves = {'hold': [entry(f'h{i}') for i in range(4)], 'lift': [entry(f'l{i}') for i in range(4)]}
        known = {e['title']: track(e['title']) for es in moves.values() for e in es}
        result, searched = self.run_fill(moves, known)
        self.assertEqual(sorted(searched), ['h0', 'h1', 'l0', 'l1'])  # 4 of 8
        self.assertEqual([len(r['tracks']) for r in result], [2, 2])

    def test_goes_further_down_a_move_only_to_replace_a_miss(self):
        moves = {'hold': [entry('h0'), entry('h1'), entry('h2'), entry('h3')]}
        result, searched = self.run_fill(moves, {'h0': track('h0'), 'h2': track('h2')})
        self.assertEqual(searched, ['h0', 'h1', 'h2'])
        self.assertEqual([t['id'] for t in result[0]['tracks']], ['h0', 'h2'])

    def test_wrong_artist_counts_as_a_miss(self):
        moves = {'hold': [entry('h0'), entry('h1'), entry('h2')]}
        result, searched = self.run_fill(moves, {'h0': track('h0', 'Someone Else'), 'h1': track('h1'), 'h2': track('h2')})
        self.assertEqual(searched, ['h0', 'h1', 'h2'])
        self.assertEqual(len(result[0]['tracks']), 2)

    def test_stops_when_a_move_runs_out(self):
        result, searched = self.run_fill({'hold': [entry('h0'), entry('h1')]}, {})
        self.assertEqual(searched, ['h0', 'h1'])
        self.assertEqual(result, [])


class SharedCache(unittest.TestCase):
    def setUp(self):
        spotify_validator._CACHE.clear()
        self.searches = []
        self.stored = {}
        patches = [
            mock.patch.object(spotify_validator, 'app_client', return_value=object()),
            mock.patch.object(spotify_validator, '_search_one', side_effect=self.fake_search),
            mock.patch.object(track_cache, 'get_many', side_effect=lambda keys: {k: v for k, v in self.stored.items() if k in keys}),
            mock.patch.object(track_cache, 'put_many', side_effect=self.stored.update),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def fake_search(self, spotify, title, artist, fallback):
        self.searches.append(title)
        result = track(title) if title != 'nope' else None
        spotify_validator._CACHE[(title.casefold(), artist.casefold(), fallback)] = result
        return result

    def test_a_second_instance_reads_instead_of_searching(self):
        batch = [entry('a'), entry('b'), entry('nope')]
        matched, failed = asyncio.run(spotify_validator.validate_songs(batch, fallback=False))
        self.assertEqual((len(matched), len(failed)), (2, 1))
        self.assertEqual(len(self.searches), 3)
        self.assertEqual(len(self.stored), 3)  # misses are shared too

        spotify_validator._CACHE.clear()  # a fresh serverless instance
        matched, failed = asyncio.run(spotify_validator.validate_songs(batch, fallback=False))
        self.assertEqual((len(matched), len(failed)), (2, 1))
        self.assertEqual(len(self.searches), 3)  # no new searches


class Concurrency(unittest.TestCase):
    def test_at_most_four_searches_in_flight(self):
        spotify_validator._CACHE.clear()
        lock, state = threading.Lock(), {'now': 0, 'peak': 0}

        def slow_search(spotify, title, artist, fallback):
            with lock:
                state['now'] += 1
                state['peak'] = max(state['peak'], state['now'])
            time.sleep(0.05)
            with lock:
                state['now'] -= 1
            return track(title)

        with mock.patch.object(spotify_validator, 'app_client', return_value=object()), \
                mock.patch.object(spotify_validator, '_search_one', side_effect=slow_search), \
                mock.patch.object(track_cache, 'get_many', return_value={}), \
                mock.patch.object(track_cache, 'put_many'):
            asyncio.run(spotify_validator.validate_songs([entry(f's{i}') for i in range(12)], fallback=False))
        self.assertLessEqual(state['peak'], 4)
        self.assertGreater(state['peak'], 1)


class Keys(unittest.TestCase):
    def test_key_ignores_case_and_spacing_but_not_fallback(self):
        self.assertEqual(track_cache.key('Redbone ', 'Childish Gambino', False), track_cache.key('redbone', 'childish gambino', False))
        self.assertNotEqual(track_cache.key('a', 'b', False), track_cache.key('a', 'b', True))

    def test_stale_misses_are_ignored(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        rows = [{'key': 'hit', 'track': {'id': 'x'}, 'created_at': (now - timedelta(days=20)).isoformat()},
                {'key': 'old-miss', 'track': None, 'created_at': (now - timedelta(days=10)).isoformat()},
                {'key': 'new-miss', 'track': None, 'created_at': (now - timedelta(days=1)).isoformat()}]
        fake = mock.Mock()
        fake.get.return_value.json.return_value = rows
        with mock.patch.object(track_cache, '_client', return_value=fake):
            self.assertEqual(track_cache.get_many(['hit', 'old-miss', 'new-miss'], now=now), {'hit': {'id': 'x'}, 'new-miss': None})


if __name__ == '__main__':
    unittest.main()
