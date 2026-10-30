import asyncio
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import genres, lastfm_client


class GenreTags(unittest.TestCase):
    def test_keeps_genres_and_merges_spellings(self):
        tags = [{'name': 'Hip-Hop', 'count': 100}, {'name': 'seen live', 'count': 90}, {'name': 'Drake', 'count': 80},
                {'name': 'hip hop', 'count': 70}, {'name': '2010s', 'count': 60}, {'name': 'rnb', 'count': 50},
                {'name': 'canadian', 'count': 40}, {'name': 'rap', 'count': 30}, {'name': 'trap', 'count': 5}]
        self.assertEqual(lastfm_client.genre_tags(tags, 'Drake'), ['hip hop', 'r&b', 'rap'])

    def test_a_tag_containing_the_artist_name_is_kept(self):
        self.assertEqual(lastfm_client.genre_tags([{'name': 'slowcore', 'count': 100}], 'Low'), ['slowcore'])


class FillGenres(unittest.TestCase):
    def test_fills_empty_genres_from_cache_then_last_fm_and_caches_new_ones(self):
        artists = [{'name': 'Drake', 'genres': []}, {'name': 'Oasis', 'genres': []}, {'name': 'Kept', 'genres': ['pop']}]
        cached = {genres.track_cache.key('lastfm-tags', 'Drake'): {'tags': ['hip hop']}}
        with mock.patch.object(genres.track_cache, 'get_many', return_value=cached), \
             mock.patch.object(genres.track_cache, 'put_many') as put, \
             mock.patch.object(genres.lastfm_client, 'artist_top_tags', mock.AsyncMock(return_value=['britpop'])) as tags:
            asyncio.run(genres.fill_genres(artists))
        self.assertEqual([a['genres'] for a in artists], [['hip hop'], ['britpop'], ['pop']])
        tags.assert_awaited_once_with('Oasis')
        self.assertEqual(list(put.call_args[0][0].values()), [{'tags': ['britpop']}])

    def test_a_failed_lookup_is_not_cached(self):
        artists = [{'name': 'X', 'genres': []}]
        with mock.patch.object(genres.track_cache, 'get_many', return_value={}), \
             mock.patch.object(genres.track_cache, 'put_many') as put, \
             mock.patch.object(genres.lastfm_client, 'artist_top_tags', mock.AsyncMock(return_value=None)):
            asyncio.run(genres.fill_genres(artists))
        self.assertEqual(artists[0]['genres'], [])
        put.assert_not_called()


if __name__ == '__main__':
    unittest.main()
