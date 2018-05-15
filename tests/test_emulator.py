from .context import Emulator
from .context import P
from .context import T
from .context import PT
from snakes.nets import Variable
from snakes.nets import Expression
from snakes.nets import Value
from snakes.nets import MultiSet
from snakes.nets import MultiArc
from snakes.nets import Place
from snakes.nets import Flush

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
        assert net.get_marking().get('P') == MultiSet([P('p0'), P('p1'), P('p2')])
        assert net.get_marking().get('T') == MultiSet([T('t0'), T('t1')])
        assert net.get_marking().get('M') == MultiSet([P('p0'), P('p1')] * 3)
        assert net.get_marking().get('I') == MultiSet([(T('t0'), P('p0')), (T('t0'), P('p1')), (T('t1'), P('p2'))])
        assert net.get_marking().get('O') == MultiSet([(T('t0'), P('p2'))])
        assert net.get_marking().get('H') == MultiSet([(T('t0'), P('p2'))] * 2)

    def test_simpleExecution(self):
        net = self.emulator.get_net()
        modes = net.transition('fire').modes()
        assert len(modes) == 1
        assert modes[0]('t') == T('t0')
        net.transition('fire').fire(modes[0])
        assert net.get_marking().get('M') == MultiSet([P('p0'), P('p1')] * 2 + [P('p2')])
        modes = net.transition('fire').modes()
        assert len(modes) == 2
        assert modes[0]('t') == T('t1')
        assert modes[1]('t') == T('t0')
        net.transition('fire').fire(modes[1])
        assert net.get_marking().get('M') == MultiSet([P('p0'), P('p1')] + [P('p2')] * 2)
        modes = net.transition('fire').modes()
        assert len(modes) == 1
        assert modes[0]('t') == T('t1')
        net.transition('fire').fire(modes[0])
        assert net.get_marking().get('M') == MultiSet([P('p0'), P('p1'), P('p2')])
        modes = net.transition('fire').modes()
        assert len(modes) == 2
        assert modes[0]('t') == T('t0')
        assert modes[1]('t') == T('t1')
        net.transition('fire').fire(modes[0])
        net.transition('fire').fire(net.transition('fire').modes()[0])
        net.transition('fire').fire(net.transition('fire').modes()[0])
        assert len(net.transition('fire').modes()) == 0

    def test_unfold(self):
        self.emulator.add_place('init')
        self.emulator.add_place('result')
        signature = 'lib::getTokens(p) := n'
        self.emulator.add_transition(signature)
        self.emulator.add_output_arc('fire', 'init', Value(P('p2')))
        self.emulator.add_input_arc('init', signature, Variable('p'))
        self.emulator.add_output_arc(signature, 'result', Variable('n'))
        self.emulator.unfold_net()
        net = self.emulator.get_net()
        assert net.place('init') is not None
        assert net.place('result') is not None
        assert net.transition(signature) is not None
        modes = net.transition('fire').modes()
        assert len(modes) == 1
        assert modes[0]('t') == T('t0')
        net.transition('fire').fire(modes[0])
        modes = net.transition('fire').modes()
        assert len(modes) == 2
        modes = net.transition(signature).modes()
        assert len(modes) == 1
        assert net.get_marking().get('result') is None
        net.transition(signature).fire(modes[0])
        assert net.get_marking().get('result') == MultiSet([1])

    def test_unfold2(self):
        self.emulator.add_place('pArg')
        self.emulator.add_place('tArg')
        self.emulator.add_place('result')
        signature = 'lib::iMult(p,t) := n'
        self.emulator.add_transition(signature)
        self.emulator.add_output_arc('fire', 'pArg', Value(P('p2')))
        self.emulator.add_output_arc('fire', 'tArg', Value(T('t1')))
        self.emulator.add_input_arc('pArg', signature, Variable('p'))
        self.emulator.add_input_arc('tArg', signature, Variable('t'))
        self.emulator.add_output_arc(signature, 'result', Variable('n'))
        self.emulator.unfold_net()
        net = self.emulator.get_net()
        modes = net.transition('fire').modes()
        assert len(modes) == 1
        assert modes[0]('t') == T('t0')
        net.transition('fire').fire(modes[0])
        modes = net.transition('fire').modes()
        assert len(modes) == 2
        modes = net.transition(signature).modes()
        assert len(modes) == 1
        assert net.get_marking().get('result') is None
        net.transition(signature).fire(modes[0])
        assert net.get_marking().get('result') == MultiSet([1])
