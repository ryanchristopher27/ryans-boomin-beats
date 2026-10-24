"""Synthetic tests for routers/dj.py parsing and selection.

Run from src/web/backend:

    python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.dj import (  # noqa: E402
    SuggestRequest, TrackRef, build_prompt, merge_recent, normalize_moves, salvage_truncated, select_tracks,
)


def _matched(title, artist, sid, artists=None, explicit=False):
    return {'title': title, 'artist': artist, 'reason': '',
            'spotify': {'id': sid, 'title': title, 'artists': artists or [artist], 'image': 'img', 'explicit': explicit}}


class NormalizeMoves(unittest.TestCase):
    def test_keeps_known_moves_and_valid_entries(self):
        data = {
            'hold': [{'title': 'A', 'artist': 'X', 'reason': 'r'}, {'title': '', 'artist': 'Y'}, 'junk'],
            'bridge': [{'title': 'B', 'artist': 'Z'}],  # not a DJ3 move
            'lift': 'not a list',
        }
        self.assertEqual(normalize_moves(data), {'hold': [{'title': 'A', 'artist': 'X', 'reason': 'r'}]})

    def test_non_object(self):
        self.assertEqual(normalize_moves([{'title': 'A', 'artist': 'X'}]), {})


class SelectTracks(unittest.TestCase):
    def test_filters_wrong_artist_excluded_and_duplicates(self):
        moves = {
            'hold': [{'title': 'A', 'artist': 'X', 'reason': 'ra'},
                     {'title': 'B', 'artist': 'Y', 'reason': 'rb'},   # title-only fallback hit
                     {'title': 'C', 'artist': 'Z', 'reason': 'rc'}],
            'lift': [{'title': 'A', 'artist': 'X', 'reason': 'dup'},  # already used by hold
                     {'title': 'D', 'artist': 'W', 'reason': 'rd'}],   # excluded (recent)
        }
        matched = [
            _matched('A', 'X', 'a'),
            _matched('B', 'Y', 'b', artists=['Someone Else']),
            _matched('C', 'Z', 'c', artists=['Z', 'Feat']),
            _matched('D', 'W', 'd'),
        ]
        result = select_tracks(moves, matched, exclude_ids={'d'}, per_move=2)
        self.assertEqual(result, [{'move': 'hold', 'tracks': [
            {'id': 'a', 'title': 'A', 'artists': ['X'], 'image': 'img', 'reason': 'ra'},
            {'id': 'c', 'title': 'C', 'artists': ['Z', 'Feat'], 'image': 'img', 'reason': 'rc'},
        ]}])

    def test_per_move_cap(self):
        moves = {'hold': [{'title': t, 'artist': 'X', 'reason': ''} for t in 'ABC']}
        matched = [_matched(t, 'X', t.lower()) for t in 'ABC']
        self.assertEqual(len(select_tracks(moves, matched, set(), per_move=2)[0]['tracks']), 2)

    def test_artist_match_is_case_insensitive_and_partial(self):
        moves = {'hold': [{'title': 'A', 'artist': 'tyler the creator', 'reason': ''}]}
        matched = [_matched('A', 'tyler the creator', 'a', artists=['Tyler, The Creator'])]
        self.assertEqual(len(select_tracks(moves, matched, set(), 2)), 1)


class DJ4Filters(unittest.TestCase):
    def setUp(self):
        self.moves = {'hold': [{'title': 'A', 'artist': 'X', 'reason': ''},
                               {'title': 'B', 'artist': 'Drake', 'reason': ''},
                               {'title': 'C', 'artist': 'Z', 'reason': ''}]}
        self.matched = [_matched('A', 'X', 'a', explicit=True),
                        _matched('B', 'Drake', 'b', artists=['Drake', 'Future']),
                        _matched('C', 'Z', 'c')]

    def ids(self, result):
        return [t['id'] for m in result for t in m['tracks']]

    def test_clean_drops_explicit(self):
        self.assertEqual(self.ids(select_tracks(self.moves, self.matched, set(), 3, clean=True)), ['b', 'c'])

    def test_avoid_artist_matches_any_credited_artist(self):
        r = select_tracks(self.moves, self.matched, set(), 3, avoid_artists=['future'])
        self.assertEqual(self.ids(r), ['a', 'c'])


class SalvageTruncated(unittest.TestCase):
    def test_keeps_complete_entries_across_moves(self):
        raw = ('{"hold": [{"title": "A", "artist": "X", "reason": "r"}], '
               '"drop": [{"title": "B", "artist": "Y", "reason": "has } and \\" inside"}, '
               '{"title": "C", "artist": "Z", "reason": "Slow-burning soul ballad')
        self.assertEqual(normalize_moves(salvage_truncated(raw)), {
            'hold': [{'title': 'A', 'artist': 'X', 'reason': 'r'}],
            'drop': [{'title': 'B', 'artist': 'Y', 'reason': 'has } and " inside'}],
        })

    def test_nothing_complete(self):
        self.assertIsNone(salvage_truncated('{"hold": [{"title": "A", "art'))
        self.assertIsNone(salvage_truncated('no json here'))


class MergeRecent(unittest.TestCase):
    def test_session_first_dedupe_and_cap(self):
        session = [TrackRef(id='1', title='S1', artist='a'), TrackRef(id='2', title='S2', artist='a')]
        spotify = [TrackRef(id='2', title='S2', artist='a'), TrackRef(id='3', title='P3', artist='b')]
        self.assertEqual([r.id for r in merge_recent(session, spotify)], ['1', '2', '3'])
        self.assertEqual(len(merge_recent(session, spotify, cap=2)), 2)


class RequestBounds(unittest.TestCase):
    def test_rejects_oversized_lists_and_strings(self):
        from pydantic import ValidationError
        np = {'title': 'A', 'artist': 'X'}
        with self.assertRaises(ValidationError):
            SuggestRequest(now_playing=np, upcoming=[np] * 51)
        with self.assertRaises(ValidationError):
            SuggestRequest(now_playing={'title': 'A' * 301, 'artist': 'X'})
        with self.assertRaises(ValidationError):
            SuggestRequest(now_playing=np, avoid_artists=['x' * 301])
        self.assertEqual(len(SuggestRequest(now_playing=np, upcoming=[np] * 50).upcoming), 50)


class SpotifyRecent(unittest.TestCase):
    def test_requests_timeout_is_best_effort(self):
        import requests
        from unittest import mock
        from routers import dj
        client = mock.Mock()
        client.current_user_recently_played.side_effect = requests.exceptions.ReadTimeout('slow')
        with mock.patch.object(dj, 'user_client', return_value=client):
            self.assertEqual(dj._spotify_recent('token'), [])


class BuildPrompt(unittest.TestCase):
    def test_dj4_context(self):
        body = SuggestRequest(
            now_playing=TrackRef(title='Redbone', artist='Childish Gambino'),
            liked=[TrackRef(title='Nights', artist='Frank Ocean')],
            skipped=[TrackRef(title='Suge', artist='DaBaby')],
            avoid_artists=['Drake'], clean=True, adventurousness=0.9,
        )
        p = build_prompt(body, [])
        for needle in ('MORE like', 'Nights — Frank Ocean', 'skipped', 'Suge — DaBaby', 'Drake', 'Clean', 'BOLD'):
            self.assertIn(needle, p)
        self.assertNotIn('LESS like', p)  # empty sections are omitted

    def test_includes_context_and_overask(self):
        body = SuggestRequest(
            now_playing=TrackRef(title='Redbone', artist='Childish Gambino'),
            recent=[TrackRef(title='Robbery', artist='Juice WRLD')],
            per_move=2,
        )
        p = build_prompt(body, ['soul', 'funk'])
        self.assertIn('Redbone — Childish Gambino', p)
        self.assertIn('soul, funk', p)
        self.assertIn('Robbery — Juice WRLD', p)
        self.assertIn('Give 4 songs', p)


if __name__ == '__main__':
    unittest.main()
