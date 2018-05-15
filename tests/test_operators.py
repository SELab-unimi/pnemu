from snakes.nets import MultiSet

import unittest
from pnemu.functions import intersection

class OperatorsTestSuite(unittest.TestCase):

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def test_intersection(self):
        result = intersection(MultiSet(['p0', 'p1']), MultiSet(['p1'] * 2))
        assert result == MultiSet(['p1'])
        result = intersection(MultiSet(['p0', 'p1']), MultiSet(['p2'] * 2))
        assert len(result) == 0

    def test_diff(self):
        a = MultiSet(['p0', 'p1'])
        b = MultiSet(['p1'] * 2)
        result = a - intersection(a, b)
        assert result == MultiSet(['p0'])
