from .context import Emulator
from .context import PT
from .context import FeedbackLoop
from .context import AdaptiveNetBuilder
from snakes.nets import Variable
from snakes.nets import Expression
from snakes.nets import Value
from snakes.nets import MultiSet
from snakes.nets import MultiArc
from snakes.nets import Place
from snakes.nets import Flush
from snakes.nets import BlackToken

import os
import unittest

MS_PNML = os.path.join(os.path.dirname(__file__), 'resources/ms.pnml')

class MSTestSuite(unittest.TestCase):

    def setup_method(self, method):
        self.pt = PT('ms', MS_PNML)
        self.emulator = Emulator(self.pt)

    def teardown_method(self, method):
        self.pt = None
        self.emulator = None

    def test_ms(self):
        loop1 = FeedbackLoop('fault-tolerance')
        loop1.add_place('init')
        loop1.add_place('result')
        assert True
