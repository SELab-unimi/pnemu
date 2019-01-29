from .context import Emulator
from .context import PT
from .context import FeedbackLoop
from .context import AdaptiveNetBuilder
from snakes.nets import Variable
from snakes.nets import Expression
from snakes.nets import Test
from snakes.nets import Value
from snakes.nets import MultiSet
from snakes.nets import MultiArc
from snakes.nets import Place
from snakes.nets import Flush
from snakes.nets import BlackToken

import os
import unittest

MS_PNML = os.path.join(os.path.dirname(__file__), 'resources/ms.pnml')
LOOP1_DOT = os.path.join(os.path.dirname(__file__), 'resources/loop1.dot')
LOOP2_DOT = os.path.join(os.path.dirname(__file__), 'resources/loop2.dot')

class MSTestSuite(unittest.TestCase):

    def setup_method(self, method):
        self.pt = PT('ms', MS_PNML)
        self.emulator = Emulator(self.pt)

    def teardown_method(self, method):
        self.pt = None
        self.emulator = None

    def test_ms(self):

        # LOOP1: fault tolerance concern

        loop1 = FeedbackLoop('fault-tolerance')
        loop1.add_place('init')
        # lock loader
        blockLoader = 'lib.addInhibitorArc("broken", "load", 1)'
        loop1.add_transition(blockLoader)
        loop1.add_input_arc('init', blockLoader, Variable('t'))
        loop1.add_place('locked')
        loop1.add_output_arc(blockLoader, 'locked', Value(BlackToken()))
        # detach loader
        detachFaulty = 'lib.removeOutputArc("line1", "load", 1)'
        loop1.add_transition(detachFaulty)
        changeWorking = 'lib.addOutputArc("line2", "load", 1)'
        loop1.add_transition(changeWorking)
        loop1.add_place('faultyDetached')
        loop1.add_input_arc('locked', detachFaulty, Value(BlackToken()))
        loop1.add_output_arc(detachFaulty, 'faultyDetached', Value(BlackToken()))
        loop1.add_input_arc('faultyDetached', changeWorking, Value(BlackToken()))
        loop1.add_place('workingChanged')
        loop1.add_output_arc(changeWorking, 'workingChanged', Value(BlackToken()))
        # wait for empty line2
        getLine2 = 'lib.getTokens("line2") := n'
        loop1.add_transition(getLine2)
        loop1.add_input_arc('workingChanged', getLine2, Value(BlackToken()))
        loop1.add_place('line2Pieces')
        loop1.add_output_arc(getLine2, 'line2Pieces', Variable('n'))
        loop1.add_transition('flush', Expression('n==0'))
        loop1.add_transition('dontFlush', Expression('n>0'))
        loop1.add_input_arc('line2Pieces', 'flush', Variable('n'))
        loop1.add_input_arc('line2Pieces', 'dontFlush', Variable('n'))
        loop1.add_output_arc('dontFlush', 'workingChanged', Value(BlackToken()))
        loop1.add_place('applyFlush')
        loop1.add_output_arc('flush', 'applyFlush', Value(BlackToken()))
        # transfer tokens from line1 to line2
        getPendings = 'lib.getTokens("line1") := n'
        loop1.add_transition(getPendings)
        loop1.add_input_arc('applyFlush', getPendings, Value(BlackToken()))
        loop1.add_place('sample')
        loop1.add_output_arc(getPendings, 'sample', Variable('n'))
        add = 'lib.setTokens("line2", n)'
        loop1.add_transition(add)
        empty = 'lib.setTokens("line1", 0)'
        loop1.add_transition(empty)
        loop1.add_input_arc('sample', add, Variable('n'))
        loop1.add_place('piecesAdded')
        loop1.add_output_arc(add, 'piecesAdded', Value(BlackToken()))
        loop1.add_input_arc('piecesAdded', empty, Value(BlackToken()))
        loop1.add_place('piecesRemoved')
        loop1.add_output_arc(empty, 'piecesRemoved', Value(BlackToken()))
        # wait for empty worked1
        getWorked1 = 'lib.getTokens("worked1") := n'
        loop1.add_transition(getWorked1)
        loop1.add_transition('changeAssembler', Expression('n==0'))
        loop1.add_transition('dontChangeAssembler', Expression('n>0'))
        loop1.add_input_arc('piecesRemoved', getWorked1, Value(BlackToken()))
        loop1.add_place('workedPieces')
        loop1.add_output_arc(getWorked1, 'workedPieces', Variable('n'))
        loop1.add_input_arc('workedPieces', 'changeAssembler', Variable('n'))
        loop1.add_input_arc('workedPieces', 'dontChangeAssembler', Variable('n'))
        loop1.add_output_arc('dontChangeAssembler', 'piecesRemoved', Value(BlackToken()))
        loop1.add_place('doChanges')
        loop1.add_output_arc('changeAssembler', 'doChanges', Value(BlackToken()))
        # change assembler and unlock loader
        addInArc = 'lib.addInputArc("worked2", "assemble", 1)'
        loop1.add_transition(addInArc)
        rmInArc = 'lib.removeInputArc("worked1", "assemble", 1)'
        loop1.add_transition(rmInArc)
        rmHArc = 'lib.removeInhibitorArc("broken", "load", 1)'
        loop1.add_transition(rmHArc)
        loop1.add_place('inAdded')
        loop1.add_place('inRemoved')
        loop1.add_place('hRemoved')
        loop1.add_input_arc('doChanges', addInArc, Value(BlackToken()))
        loop1.add_output_arc(addInArc, 'inAdded', Value(BlackToken()))
        loop1.add_input_arc('inAdded', rmInArc, Value(BlackToken()))
        loop1.add_output_arc(rmInArc, 'inRemoved', Value(BlackToken()))
        loop1.add_input_arc('inRemoved', rmHArc, Value(BlackToken()))
        loop1.add_output_arc(rmHArc, 'hRemoved', Value(BlackToken()))
        # set fixable
        addFixArc = 'lib.addInputArc("broken", "repair", 1)'
        loop1.add_transition(addFixArc)
        lockFailArc = 'lib.addInhibitorArc("fixing", "fail", 1)'
        loop1.add_transition(lockFailArc)
        rmFixInhArc = 'lib.removeInhibitorArc("fixing", "repair", 1)'
        loop1.add_transition(rmFixInhArc)
        loop1.add_place('fixArcAdded')
        loop1.add_place('lockFailArcAdded')
        loop1.add_input_arc('hRemoved', addFixArc, Value(BlackToken()))
        loop1.add_output_arc(addFixArc, 'fixArcAdded', Value(BlackToken()))
        loop1.add_input_arc('fixArcAdded', lockFailArc, Value(BlackToken()))
        loop1.add_output_arc(lockFailArc, 'lockFailArcAdded', Value(BlackToken()))
        loop1.add_input_arc('lockFailArcAdded', rmFixInhArc, Value(BlackToken()))

        #loop1.draw(LOOP1_DOT, render=True)

        # LOOP2: load balancing concern

        loop2 = FeedbackLoop('load-balancing')
        loop2.add_place('init2')
        # lock loader
        blockLoader2 = 'lib.addInputArc(p, "load", 1)'
        loop2.add_transition(blockLoader2)
        loop2.add_place('inHIn', ['broken'])
        loop2.add_input_arc('init2', blockLoader2, Variable('t'))
        loop2.add_input_arc('inHIn', blockLoader2, Variable('p'))
        loop2.add_output_arc(blockLoader2, 'inHIn', Variable('p'))
        loop2.add_place('locked2')
        loop2.add_output_arc(blockLoader2, 'locked2', Value(BlackToken()))
        # attach loader
        attachFaulty = 'lib.addOutputArc("line1", "load", 1)'
        loop2.add_transition(attachFaulty)
        decWorking = 'lib.removeOutputArc("line2", "load", 1)'
        loop2.add_transition(decWorking)
        loop2.add_place('faultyAttached')
        loop2.add_place('loaderChanged')
        loop2.add_input_arc('locked2', attachFaulty, Value(BlackToken()))
        loop2.add_output_arc(attachFaulty, 'faultyAttached', Value(BlackToken()))
        loop2.add_input_arc('faultyAttached', decWorking, Value(BlackToken()))
        loop2.add_output_arc(decWorking, 'loaderChanged', Value(BlackToken()))
        # wait for empty line2, worked2
        getLine2Bis = 'lib.getTokens("line2") := m'
        loop2.add_transition(getLine2Bis)
        loop2.add_transition('line2Empty', Expression('m==0'))
        loop2.add_transition('line2NotEmpty', Expression('m>0'))
        loop2.add_input_arc('loaderChanged', getLine2Bis, Value(BlackToken()))
        loop2.add_place('line2Sample')
        loop2.add_place('emptyCheckPassed')
        loop2.add_output_arc(getLine2Bis, 'line2Sample', Variable('m'))
        loop2.add_input_arc('line2Sample', 'line2Empty', Variable('m'))
        loop2.add_input_arc('line2Sample', 'line2NotEmpty', Variable('m'))
        loop2.add_output_arc('line2NotEmpty', 'loaderChanged', Value(BlackToken()))
        loop2.add_output_arc('line2Empty', 'emptyCheckPassed', Value(BlackToken()))
        getWorked2 = 'lib.getTokens("worked2") := n'
        loop2.add_transition(getWorked2)
        loop2.add_input_arc('emptyCheckPassed', getWorked2, Value(BlackToken()))
        loop2.add_place('worked2Pieces')
        loop2.add_output_arc(getWorked2, 'worked2Pieces', Variable('n'))
        loop2.add_transition('proceed', Expression('n==0'))
        loop2.add_transition('wait', Expression('n>0'))
        loop2.add_input_arc('worked2Pieces', 'proceed', Variable('n'))
        loop2.add_input_arc('worked2Pieces', 'wait', Variable('n'))
        loop2.add_output_arc('wait', 'emptyCheckPassed', Value(BlackToken()))
        loop2.add_place('emptyWorked')
        loop2.add_output_arc('proceed', 'emptyWorked', Value(BlackToken()))
        # change assembler and unlock loader
        addInArc2 = 'lib.addInputArc("worked1", "assemble", 1)'
        loop2.add_transition(addInArc2)
        rmInArc2 = 'lib.removeInputArc("worked2", "assemble", 1)'
        loop2.add_transition(rmInArc2)
        rmHArc2 = 'lib.removeInputArc(p, "load", 1)'
        loop2.add_transition(rmHArc2)
        loop2.add_place('inAdded2')
        loop2.add_place('inRemoved2')
        loop2.add_place('hRemoved2')
        loop2.add_input_arc('emptyWorked', addInArc2, Value(BlackToken()))
        loop2.add_output_arc(addInArc2, 'inAdded2', Value(BlackToken()))
        loop2.add_input_arc('inAdded2', rmInArc2, Value(BlackToken()))
        loop2.add_output_arc(rmInArc2, 'inRemoved2', Value(BlackToken()))
        loop2.add_input_arc('inRemoved2', rmHArc2, Value(BlackToken()))
        loop2.add_input_arc('inHIn', rmHArc2, Variable('p'))
        loop2.add_output_arc(rmHArc2, 'inHIn', Variable('p'))
        loop2.add_output_arc(rmHArc2, 'hRemoved2', Value(BlackToken()))
        # set faulty behavior
        addFixHArc = 'lib.addInhibitorArc("fixing", "repair", 1)'
        loop2.add_transition(addFixHArc)
        rmRepairArc = 'lib.removeInputArc("broken", "repair", 1)'
        loop2.add_transition(rmRepairArc)
        rmLockfailArc = 'lib.removeInhibitorArc("fixing", "fail", 1)'
        loop2.add_transition(rmLockfailArc)
        loop2.add_place('fixHArcAdded')
        loop2.add_place('repairArcRemoved')
        loop2.add_input_arc('hRemoved2', addFixHArc, Value(BlackToken()))
        loop2.add_output_arc(addFixHArc, 'fixHArcAdded', Value(BlackToken()))
        loop2.add_input_arc('fixHArcAdded', rmRepairArc, Value(BlackToken()))
        loop2.add_output_arc(rmRepairArc, 'repairArcRemoved', Value(BlackToken()))
        loop2.add_input_arc('repairArcRemoved', rmLockfailArc, Value(BlackToken()))

        #loop2.draw(LOOP2_DOT, render=True)

        net = AdaptiveNetBuilder(self.emulator)     \
            .add_loop(loop1, ['init'], ['fail'])    \
            .add_loop(loop2, ['init2'], ['repair']) \
            .build()

        # token game example

        self.fire_lowLevel(net, 'load')
        assert net.get_marking().get('M')('line1') == 1
        assert net.get_marking().get('M')('line2') == 1
        self.fire_lowLevel(net, 'fail')
        assert net.get_marking().get('M')('broken') == 1
        self.fire_highLevel(net, blockLoader)
        assert net.get_marking().get('H')(('load','broken')) == 1
        assert net.get_marking().get('locked') == MultiSet([BlackToken()])
        self.fire_highLevel(net, detachFaulty)
        self.fire_highLevel(net, changeWorking)
        assert net.get_marking().get('O')(('load','line1')) == 0
        assert net.get_marking().get('O')(('load','line2')) == 2
        self.fire_lowLevel(net, 'work2')
        self.fire_highLevel(net, getLine2)
        assert net.get_marking().get('line2Pieces') == MultiSet([0])
        self.fire_highLevel(net, 'flush')
        self.fire_highLevel(net, getPendings)
        self.fire_highLevel(net, add)
        self.fire_highLevel(net, empty)
        assert net.get_marking().get('M')('line1') == 0
        assert net.get_marking().get('M')('line2') == 1
        self.fire_highLevel(net, getWorked1)
        assert net.get_marking().get('workedPieces') == MultiSet([0])
        self.fire_highLevel(net, 'changeAssembler')
        self.fire_highLevel(net, addInArc)
        assert net.get_marking().get('inAdded') == MultiSet([BlackToken()])
        self.fire_highLevel(net, rmInArc)
        assert net.get_marking().get('inRemoved') == MultiSet([BlackToken()])
        self.fire_highLevel(net, rmHArc)
        assert net.get_marking().get('hRemoved') == MultiSet([BlackToken()])
        self.fire_highLevel(net, addFixArc)
        assert net.get_marking().get('fixArcAdded') == MultiSet([BlackToken()])
        self.fire_highLevel(net, lockFailArc)
        assert net.get_marking().get('lockFailArcAdded') == MultiSet([BlackToken()])
        self.fire_highLevel(net, rmFixInhArc)
        assert net.get_marking().get('M')('broken') == 1
        assert net.get_marking().get('I')(('assemble', 'worked1')) == 0
        assert net.get_marking().get('I')(('assemble', 'worked2')) == 2
        assert net.get_marking().get('I')(('repair', 'broken')) == 1
        assert net.get_marking().get('H')(('load', 'broken')) == 0
        assert net.get_marking().get('H')(('repair', 'fixing')) == 0
        assert net.get_marking().get('H')(('fail', 'fixing')) == 1
        assert net.get_marking().get('M')('fixing') == 1
        self.fire_lowLevel(net, 'repair')
        assert net.get_marking().get('init2') == MultiSet(['repair'])

    def fire_lowLevel(self, net, transition):
        mode = None
        modes = net.transition('move').modes()
        for m in modes:
            if m('t') == transition:
                mode = m
                assert mode('t') == transition
                net.transition('move').fire(mode)
                return
        if mode is None or mode('t') != transition:
            modes = net.transition('move1').modes()
            for m in modes:
                if m('t') == transition:
                    mode = m
                    assert mode('t') == transition
                    net.transition('move1').fire(mode)
                    return
        if mode is None or mode('t') != transition:
            modes = net.transition('move2').modes()
            for m in modes:
                if m('t') == transition:
                    mode = m
                    assert mode('t') == transition
                    net.transition('move2').fire(mode)
                    return
        assert False

    def fire_highLevel(self, net, transition):
        modes = net.transition(transition).modes()
        assert len(modes) > 0
        net.transition(transition).fire(modes[0])
