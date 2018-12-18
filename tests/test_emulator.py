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

STRATEGY_PNML = os.path.join(os.path.dirname(__file__), 'resources/strategy-example.pnml')
EXPORT_PNML = os.path.join(os.path.dirname(__file__), 'resources/export-example.pnml')

class EmulatorTestSuite(unittest.TestCase):

    def setup_method(self, method):
        self.pt = PT('PT-net-example')
        self.pt.add_place('p0', 3)
        self.pt.add_place('p1', 3)
        self.pt.add_place('p2')
        self.pt.add_transition('t0')
        self.pt.add_transition('t1')
        self.pt.add_input_arc('p0', 't0')
        self.pt.add_input_arc('p1', 't0')
        self.pt.add_output_arc('t0', 'p2')
        self.pt.add_inhibitor_arc('p2', 't0', 2)
        self.pt.add_input_arc('p2', 't1')
        self.emulator = Emulator(self.pt)

    def teardown_method(self, method):
        self.strategy = None

    def test_contruction(self):
        net = self.emulator.get_net()
        assert net.get_marking().get('P') == MultiSet(['p0', 'p1', 'p2'])
        assert net.get_marking().get('T') == MultiSet(['t0', 't1'])
        assert net.get_marking().get('M') == MultiSet(['p0', 'p1'] * 3)
        assert net.get_marking().get('I') == MultiSet([('t0', 'p0'), ('t0', 'p1'), ('t1', 'p2')])
        assert net.get_marking().get('O') == MultiSet([('t0', 'p2')])
        assert net.get_marking().get('H') == MultiSet([('t0', 'p2')] * 2)

    def test_simpleExecution(self):
        net = self.emulator.get_net()
        modes = net.transition('move').modes()
        assert len(modes) == 1
        assert modes[0]('t') == 't0'
        net.transition('move').fire(modes[0])
        assert net.get_marking().get('M') == MultiSet(['p0', 'p1'] * 2 + ['p2'])
        modes = net.transition('move').modes()
        assert len(modes) == 2
        assert modes[0]('t') == 't1' or modes[0]('t') == 't0'
        assert modes[1]('t') == 't1' or modes[1]('t') == 't0'
        selectedMode = modes[0]
        if modes[1]('t') == 't0':
            selectedMode = modes[1]
        net.transition('move').fire(selectedMode)
        assert net.get_marking().get('M') == MultiSet(['p0', 'p1'] + ['p2'] * 2)
        modes = net.transition('move').modes()
        assert len(modes) == 1
        assert modes[0]('t') == 't1'
        net.transition('move').fire(modes[0])
        assert net.get_marking().get('M') == MultiSet(['p0', 'p1', 'p2'])
        modes = net.transition('move').modes()
        assert len(modes) == 2
        assert modes[0]('t') == 't0'
        assert modes[1]('t') == 't1'
        net.transition('move').fire(modes[0])
        net.transition('move').fire(net.transition('move').modes()[0])
        net.transition('move').fire(net.transition('move').modes()[0])
        assert len(net.transition('move').modes()) == 0

    def test_unfold(self):
        loop = FeedbackLoop('loop-test')
        loop.add_place('init')
        loop.add_place('result')
        signature = 'lib.getTokens("p2") := n'
        loop.add_transition(signature)
        loop.add_input_arc('init', signature, Variable('p'))
        loop.add_output_arc(signature, 'result', Variable('n'))
        net = AdaptiveNetBuilder(self.emulator).add_loop(loop, 'init').build()
        assert net.place('init') is not None
        assert net.place('result') is not None
        assert net.transition(signature) is not None
        modes = net.transition('move').modes()
        assert len(modes) == 1
        assert modes[0]('t') == 't0'
        net.transition('move').fire(modes[0])
        modes = net.transition('move').modes()
        assert len(modes) == 2
        modes = net.transition(signature).modes()
        assert len(modes) == 1
        assert net.get_marking().get('result') is None
        net.transition(signature).fire(modes[0])
        assert net.get_marking().get('result') == MultiSet([1])

    def test_unfold2(self):
        loop = FeedbackLoop('loop-test')
        loop.add_place('init')
        loop.add_place('pArg', ['p2'])
        loop.add_place('tArg', ['t1'])
        loop.add_place('result')
        signature = 'lib.iMult(p,t) := n'
        loop.add_transition(signature)
        loop.add_input_arc('init', signature, Value(BlackToken()))
        loop.add_input_arc('pArg', signature, Variable('p'))
        loop.add_input_arc('tArg', signature, Variable('t'))
        loop.add_output_arc(signature, 'result', Variable('n'))
        net = AdaptiveNetBuilder(self.emulator).add_loop(loop, 'init').build()
        modes = net.transition('move').modes()
        assert len(modes) == 1
        assert modes[0]('t') == 't0'
        net.transition('move').fire(modes[0])
        modes = net.transition('move').modes()
        assert len(modes) == 2
        modes = net.transition(signature).modes()
        assert len(modes) == 1
        assert net.get_marking().get('result') is None
        net.transition(signature).fire(modes[0])
        assert net.get_marking().get('result') == MultiSet([1])
