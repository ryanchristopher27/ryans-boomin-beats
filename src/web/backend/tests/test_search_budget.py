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
from services import track_cache  # noqa: E402


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


class DeezerChecks(unittest.TestCase):
    """Q2: picks are checked on Deezer; played/queued songs drop by ISRC or title."""

    def run_round(self, moves, found, exclude=frozenset(), exclude_keys=frozenset(), clean=False):
        from routers import dj
        from services import deezer

        async def fake_find_many(batch):
            return {(e['title'], e['artist']): found.get(e['title']) for e in batch}
        with mock.patch.object(deezer, 'find_many', side_effect=fake_find_many):
            return asyncio.run(dj.fill_moves(moves, set(exclude), 2, clean=clean, exclude_keys=set(exclude_keys)))

    def song(self, title, isrc, explicit=False, artist='A'):
        return {'deezer_id': 1, 'title': title, 'artists': [artist], 'image': 'img', 'explicit': explicit, 'isrc': isrc}

    def test_picks_carry_isrc_and_no_spotify_id(self):
        result = self.run_round({'hold': [entry('a'), entry('b')]}, {'a': self.song('a', 'USAAA0000001'), 'b': self.song('b', None)})
        tracks = result[0]['tracks']
        self.assertEqual([t['id'] for t in tracks], ['USAAA0000001', 'dz:1'])
        self.assertEqual(tracks[0]['isrc'], 'USAAA0000001')

    def test_played_songs_are_excluded_by_isrc_or_title(self):
        from routers.dj import song_key
        moves = {'hold': [entry('a'), entry('b'), entry('c')]}
        found = {t: self.song(t, f'USAAA000000{i}') for i, t in enumerate('abc')}
        result = self.run_round(moves, found, exclude={'USAAA0000000'}, exclude_keys={song_key('b', 'A')})
        self.assertEqual([t['title'] for t in result[0]['tracks']], ['c'])

    def test_clean_uses_deezers_explicit_flag(self):
        found = {'a': self.song('a', 'USAAA0000001', explicit=True), 'b': self.song('b', 'USAAA0000002')}
        result = self.run_round({'hold': [entry('a'), entry('b')]}, found, clean=True)
        self.assertEqual([t['title'] for t in result[0]['tracks']], ['b'])


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
