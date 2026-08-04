"""Synthetic tests for LLM output parsing.

The BYOK design means the server never holds provider keys, so these cover the
malformed shapes the three providers actually emit rather than calling them
live. Run from src/web/backend:

    python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.llm_playlist import _normalize_suggestions  # noqa: E402
from routers.song_profile import _coerce_score, _parse_analysis  # noqa: E402
from services.llm_json import LLMParseError, extract_json  # noqa: E402

GOOD_PROFILE = """{
  "analysis": {"Mood": "Restless.", "Instrumentation": "Slide guitar.",
               "Lyrical Themes": "The road.", "Era": "1970s.",
               "Cultural Context": "Southern rock."},
  "scores": {"Energy": 60, "Danceability": 40, "Positivity": 55,
             "Acousticness": 35, "Intensity": 50, "Tempo": 58},
  "tags": ["southern rock", "1970s"]
}"""


class TestExtractJson(unittest.TestCase):
    def test_bare_object(self):
        self.assertEqual(extract_json('{"a": 1}'), {'a': 1})

    def test_json_fence(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {'a': 1})

    def test_bare_fence(self):
        self.assertEqual(extract_json('```\n{"a": 1}\n```'), {'a': 1})

    def test_tilde_fence(self):
        self.assertEqual(extract_json('~~~\n{"a": 1}\n~~~'), {'a': 1})

    def test_prose_before(self):
        # Groq/Llama does this constantly.
        self.assertEqual(extract_json('Here is the analysis:\n{"a": 1}'), {'a': 1})

    def test_prose_after(self):
        self.assertEqual(extract_json('{"a": 1}\n\nLet me know if you want more!'), {'a': 1})

    def test_prose_both_sides_with_fence(self):
        raw = 'Sure!\n\n```json\n{"a": 1}\n```\n\nHope that helps.'
        self.assertEqual(extract_json(raw), {'a': 1})

    def test_array(self):
        self.assertEqual(extract_json('[{"t": 1}]'), [{'t': 1}])

    def test_braces_inside_strings_do_not_break_balance(self):
        raw = 'note:\n{"reason": "a song about {braces} and \\"quotes\\""}'
        self.assertEqual(extract_json(raw), {'reason': 'a song about {braces} and "quotes"'})

    def test_nested_objects(self):
        raw = 'text {"a": {"b": [1, 2, {"c": 3}]}} trailing'
        self.assertEqual(extract_json(raw), {'a': {'b': [1, 2, {'c': 3}]}})

    def test_empty_raises(self):
        with self.assertRaises(LLMParseError):
            extract_json('   ')

    def test_pure_prose_raises(self):
        with self.assertRaises(LLMParseError):
            extract_json("I can't help with that request.")

    def test_error_carries_snippet(self):
        try:
            extract_json('I refuse.\nThis is not JSON.')
        except LLMParseError as e:
            self.assertIn('I refuse.', e.snippet)
        else:
            self.fail('expected LLMParseError')


class TestCoerceScore(unittest.TestCase):
    def test_int(self):
        self.assertEqual(_coerce_score(85), 85)

    def test_float(self):
        self.assertEqual(_coerce_score(85.7), 85)

    def test_numeric_string(self):
        self.assertEqual(_coerce_score('85'), 85)

    def test_clamps(self):
        self.assertEqual(_coerce_score(140), 100)
        self.assertEqual(_coerce_score(-5), 0)

    def test_bool_rejected(self):
        # isinstance(True, int) is True — this used to read as 1.
        self.assertIsNone(_coerce_score(True))

    def test_garbage_rejected(self):
        self.assertIsNone(_coerce_score('high'))
        self.assertIsNone(_coerce_score(None))


class TestParseAnalysis(unittest.TestCase):
    def test_well_formed(self):
        result = _parse_analysis(GOOD_PROFILE)
        self.assertIsNone(result['error'])
        self.assertEqual(result['scores']['Energy'], 60)
        self.assertIn('southern rock', result['tags'])
        self.assertIn('Mood: Restless.', result['analysis_text'])

    def test_fenced(self):
        result = _parse_analysis(f'```json\n{GOOD_PROFILE}\n```')
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['scores'])

    def test_lowercase_score_keys(self):
        raw = GOOD_PROFILE.replace('"Energy"', '"energy"').replace('"Tempo"', '"tempo"')
        result = _parse_analysis(raw)
        self.assertIsNotNone(result['scores'], 'lowercase keys should still populate the radar')
        self.assertEqual(result['scores']['Energy'], 60)

    def test_string_scores(self):
        raw = GOOD_PROFILE.replace(': 60,', ': "60",')
        self.assertEqual(_parse_analysis(raw)['scores']['Energy'], 60)

    def test_missing_one_score_reports_which(self):
        raw = GOOD_PROFILE.replace('"Tempo": 58', '"Tempo": "unknown"')
        result = _parse_analysis(raw)
        self.assertIsNone(result['scores'], 'a partial set would render a misleading radar')
        self.assertIn('Tempo', result['error'])
        self.assertIsNotNone(result['analysis_text'], 'analysis text should survive bad scores')

    def test_unparseable_sets_error(self):
        result = _parse_analysis('I cannot analyze that song.')
        self.assertIsNone(result['analysis_text'])
        self.assertIn('valid JSON', result['error'])

    def test_array_instead_of_object(self):
        result = _parse_analysis('[1, 2, 3]')
        self.assertIn('expected an object', result['error'])

    def test_missing_analysis_section(self):
        result = _parse_analysis('{"scores": {}, "tags": []}')
        self.assertIsNone(result['analysis_text'])
        self.assertIn('analysis', result['error'])

    def test_tags_not_a_list(self):
        raw = GOOD_PROFILE.replace('["southern rock", "1970s"]', '"southern rock"')
        self.assertEqual(_parse_analysis(raw)['tags'], [])


class TestNormalizeSuggestions(unittest.TestCase):
    def test_plain_array(self):
        data = [{'title': 'A', 'artist': 'B', 'reason': 'C'}]
        self.assertEqual(len(_normalize_suggestions(data)), 1)

    def test_wrapped_in_object(self):
        # "respond ONLY with a JSON array" ignored — very common.
        data = {'playlist': [{'title': 'A', 'artist': 'B'}]}
        out = _normalize_suggestions(data)
        self.assertEqual(out[0]['title'], 'A')
        self.assertEqual(out[0]['reason'], '')

    def test_alternate_wrapper_keys(self):
        for key in ('songs', 'tracks', 'results', 'items'):
            out = _normalize_suggestions({key: [{'title': 'A', 'artist': 'B'}]})
            self.assertEqual(len(out), 1, f'wrapper key {key!r} not handled')

    def test_single_object(self):
        self.assertEqual(len(_normalize_suggestions({'title': 'A', 'artist': 'B'})), 1)

    def test_drops_entries_missing_fields(self):
        data = [
            {'title': 'A', 'artist': 'B'},
            {'title': 'no artist'},
            {'artist': 'no title'},
            {'title': '  ', 'artist': 'blank'},
            'a bare string',
            None,
        ]
        out = _normalize_suggestions(data)
        self.assertEqual(len(out), 1, 'only the well-formed entry should survive')

    def test_scalar_returns_empty(self):
        self.assertEqual(_normalize_suggestions('nope'), [])
        self.assertEqual(_normalize_suggestions(42), [])

    def test_coerces_non_string_fields(self):
        out = _normalize_suggestions([{'title': 123, 'artist': 456}])
        self.assertEqual(out[0]['title'], '123')


if __name__ == '__main__':
    unittest.main(verbosity=2)
