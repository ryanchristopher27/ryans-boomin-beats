import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.churn import compare

ids = lambda *xs: [{'id': x} for x in xs]  # noqa: E731


class Churn(unittest.TestCase):
    def test_new_staples_rising_fading(self):
        medium = ids(*[f'm{i}' for i in range(20)], 'riser')  # riser is #21 over 6 months
        short = ids('fresh', 'riser', 'm0', 'old')
        long = ids('m0', 'old', 'gone')
        r = compare(short, medium, long)
        self.assertEqual([x['id'] for x in r['new']], ['fresh'])
        self.assertEqual([x['id'] for x in r['staples']], ['m0'])
        self.assertEqual([x['id'] for x in r['rising']], ['riser'])
        self.assertEqual(r['rising'][0]['ranks'], {'short': 2, 'medium': 21, 'long': None})
        self.assertEqual([x['id'] for x in r['fading']], ['gone'])

    def test_empty(self):
        self.assertEqual(compare([], [], []), {'new': [], 'staples': [], 'rising': [], 'fading': []})


if __name__ == '__main__':
    unittest.main()
