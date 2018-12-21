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
        loop1.add_place('breakSample')
        getTokens = 'lib.getTokens("broken") := n'
        loop1.add_transition(getTokens)
        loop1.add_input_arc('init', getTokens, Value(BlackToken()))
        loop1.add_output_arc(getTokens, 'breakSample', Variable('n'))
        loop1.add_transition('broken', Expression('n>0'))
        loop1.add_transition('notBroken', Expression('n==0'))
        loop1.add_input_arc('breakSample', 'broken', Variable('n'))
        loop1.add_input_arc('breakSample', 'notBroken', Variable('n'))
        loop1.add_place('faulireState')
        loop1.add_output_arc('broken', 'faulireState', Value(BlackToken()))
        hMult = 'lib.hMult("broken", "load") := m'
        loop1.add_transition(hMult)
        loop1.add_input_arc('faulireState', hMult, Value(BlackToken()))
        loop1.add_place('multSample')
        loop1.add_output_arc(hMult, 'multSample', Variable('m'))
        blockLoader = 'lib.addInhibitorArc("broken", "load", 1)'
        loop1.add_transition(blockLoader, Expression('m==0'))
        loop1.add_transition('dontBlock', Expression('m>0'))
        loop1.add_input_arc('multSample', blockLoader, Variable('m'))
        loop1.add_input_arc('multSample', 'dontBlock', Variable('m'))
        loop1.add_place('blockedLoader')
        loop1.add_output_arc(blockLoader, 'blockedLoader', Value(BlackToken()))
        detachLoader = 'lib.removeOutputArc("line1", "load", 1)'
        loop1.add_transition(detachLoader)
        addLoaderOut = 'lib.addOutputArc("line2", "load", 1)'
        loop1.add_transition(addLoaderOut)
        loop1.add_place('addLoaderOut')
        loop1.add_input_arc('blockedLoader', detachLoader, Value(BlackToken()))
        loop1.add_place('samplePending')
        loop1.add_place('sampleLine2')
        loop1.add_output_arc(detachLoader, 'addLoaderOut', Value(BlackToken()))
        loop1.add_input_arc('addLoaderOut', addLoaderOut, Value(BlackToken()))
        loop1.add_output_arc(addLoaderOut, 'samplePending', Value(BlackToken()))
        loop1.add_output_arc(detachLoader, 'sampleLine2', Value(BlackToken()))
        getPendings = 'lib.getTokens("line1") := n'
        loop1.add_transition(getPendings)
        getLine2 = 'lib.getTokens("line2") := m'
        loop1.add_transition(getLine2)
        loop1.add_input_arc('samplePending', getPendings, Value(BlackToken()))
        loop1.add_input_arc('sampleLine2', getLine2, Value(BlackToken()))
        loop1.add_place('pendingPieces')
        loop1.add_place('line2Pieces')
        loop1.add_output_arc(getPendings, 'pendingPieces', Variable('n'))
        loop1.add_output_arc(getLine2, 'line2Pieces', Variable('m'))
        loop1.add_transition('flush', Expression('n>0 and m==0'))
        loop1.add_transition('dontFlush', Expression('not(n>0 and m==0)'))
        loop1.add_input_arc('pendingPieces', 'flush', Test(Variable('n')))
        loop1.add_input_arc('line2Pieces', 'flush', Variable('m'))
        loop1.add_input_arc('pendingPieces', 'dontFlush', Variable('n'))
        loop1.add_input_arc('line2Pieces', 'dontFlush', Variable('m'))
        loop1.add_output_arc('dontFlush', 'samplePending', Variable('h'))
        loop1.add_output_arc('dontFlush', 'sampleLine2', Variable('h'))
        loop1.add_place('applyFlush')
        loop1.add_output_arc('flush', 'applyFlush', Value(BlackToken()))
        empty = 'lib.setTokens("line1", 0)'
        loop1.add_transition(empty)
        add = 'lib.setTokens("line2", n)'
        loop1.add_transition(add)
        loop1.add_input_arc('applyFlush', empty, Value(BlackToken()))
        loop1.add_place('piecesRemoved')
        loop1.add_output_arc(empty, 'piecesRemoved', Value(BlackToken()))
        loop1.add_input_arc('piecesRemoved', add, Value(BlackToken()))
        loop1.add_input_arc('pendingPieces', add, Variable('n'))
        loop1.add_place('sampleWorked')
        loop1.add_place('workedPieces')
        getWorked1 = 'lib.getTokens("worked1") := n'
        loop1.add_transition(getWorked1)
        loop1.add_transition('changeAssembler', Expression('n==0'))
        loop1.add_transition('dontChangeAssembler', Expression('n>0'))
        loop1.add_output_arc(add, 'sampleWorked', Value(BlackToken()))
        loop1.add_input_arc('sampleWorked', getWorked1, Value(BlackToken()))
        loop1.add_output_arc(getWorked1, 'workedPieces', Variable('n'))
        loop1.add_input_arc('workedPieces', 'changeAssembler', Variable('n'))
        loop1.add_input_arc('workedPieces', 'dontChangeAssembler', Variable('n'))
        loop1.add_output_arc('dontChangeAssembler', 'sampleWorked', Value(BlackToken()))
        loop1.add_place('doChanges')
        addInArc = 'lib.addInputArc("worked2", "assemble", 1)'
        loop1.add_transition(addInArc)
        rmInArc = 'lib.removeInputArc("worked1", "assemble", 1)'
        loop1.add_transition(rmInArc)
        rmHArc = 'lib.removeInhibitortArc("broken", "load", 1)'
        loop1.add_transition(rmHArc)
        loop1.add_place('inAdded')
        loop1.add_place('inRemoved')
        loop1.add_place('hRemoved')
        loop1.add_output_arc('changeAssembler', 'doChanges', Value(BlackToken()))
        loop1.add_input_arc('doChanges', addInArc, Value(BlackToken()))
        loop1.add_output_arc(addInArc, 'inAdded', Value(BlackToken()))
        loop1.add_input_arc('inAdded', rmInArc, Value(BlackToken()))
        loop1.add_output_arc(rmInArc, 'inRemoved', Value(BlackToken()))
        loop1.add_input_arc('inRemoved', rmHArc, Value(BlackToken()))
        loop1.add_output_arc(rmHArc, 'hRemoved', Value(BlackToken()))
        addFixTr = 'lib.addTransition("fix")'
        loop1.add_transition(addFixTr)
        loop1.add_place('fixTrAdded')
        addFixArc = 'lib.addInputArc("broken", "fix", 1)'
        loop1.add_transition(addFixArc)
        loop1.add_input_arc('hRemoved', addFixTr, Value(BlackToken()))
        loop1.add_output_arc(addFixTr, 'fixTrAdded', Value(BlackToken()))
        loop1.add_input_arc('fixTrAdded', addFixArc, Value(BlackToken()))

        #loop1.draw(LOOP1_DOT, render=True)

        # LOOP2: load balancing concern

        loop2 = FeedbackLoop('load-balancing')
        loop2.add_place('init21')
        loop2.add_place('init22')
        loop2.add_place('breakSample2')
        loop2.add_place('fixSample')
        getTokens2 = 'lib.getTokens("broken") := m'
        loop2.add_transition(getTokens2)
        fixExist = 'lib.exists("fix") := b'
        loop2.add_transition(fixExist)
        loop2.add_input_arc('init21', getTokens2, Value(BlackToken()))
        loop2.add_input_arc('init22', fixExist, Value(BlackToken()))
        loop2.add_output_arc(getTokens2, 'breakSample2', Variable('m'))
        loop2.add_output_arc(fixExist, 'fixSample', Variable('b'))
        loop2.add_transition('fixed', Expression('m==0 and b'))
        loop2.add_transition('notFixed', Expression('not(m==0 and b)'))
        loop2.add_input_arc('breakSample2', 'fixed', Variable('m'))
        loop2.add_input_arc('breakSample2', 'notFixed', Variable('m'))
        loop2.add_input_arc('fixSample', 'fixed', Variable('b'))
        loop2.add_input_arc('fixSample', 'notFixed', Variable('b'))
        loop2.add_place('blockLoader2')
        loop2.add_output_arc('fixed', 'blockLoader2', Value(BlackToken()))
        blockLoader2 = 'lib.addInhibitorArc(p, "load", 1)'
        loop2.add_transition(blockLoader2)
        loop2.add_place('inHIn', ['broken'])
        loop2.add_input_arc('blockLoader2', blockLoader2, Value(BlackToken()))
        loop2.add_input_arc('inHIn', blockLoader2, Test(Variable('p')))
        loop2.add_place('sampleLine2Bis')
        loop2.add_place('sampleWorked2Bis')
        line2Sample = 'lib.getTokens("line2") := l'
        loop2.add_transition(line2Sample)
        worked2Sample = 'lib.getTokens("worked2") := w'
        loop2.add_transition(worked2Sample)
        loop2.add_output_arc(blockLoader2, 'sampleLine2Bis', Value(BlackToken()))
        loop2.add_output_arc(blockLoader2, 'sampleWorked2Bis', Value(BlackToken()))
        loop2.add_input_arc('sampleLine2Bis', line2Sample, Value(BlackToken()))
        loop2.add_input_arc('sampleWorked2Bis', worked2Sample, Value(BlackToken()))
        loop2.add_place('line2BisRes')
        loop2.add_place('worked2BisRes')
        loop2.add_output_arc(line2Sample, 'line2BisRes', Variable('l'))
        loop2.add_output_arc(worked2Sample, 'worked2BisRes', Variable('w'))
        loop2.add_transition('attachLoader', Expression('l==0 and w==0'))
        loop2.add_transition('dontAttachLoader', Expression('not(l==0 and w==0)'))
        loop2.add_input_arc('line2BisRes', 'attachLoader', Variable('l'))
        loop2.add_input_arc('line2BisRes', 'dontAttachLoader', Variable('l'))
        loop2.add_input_arc('worked2BisRes', 'attachLoader', Variable('w'))
        loop2.add_input_arc('worked2BisRes', 'dontAttachLoader', Variable('w'))
        loop2.add_output_arc('dontAttachLoader', 'sampleLine2Bis', Variable('w'))
        loop2.add_output_arc('dontAttachLoader', 'sampleWorked2Bis', Variable('w'))
        loop2.add_place('doChanges2')
        loop2.add_output_arc('attachLoader', 'doChanges2', Value(BlackToken()))
        rmLoaderOut2 = 'lib.addOutputArc("line1", "load", 1)'
        loop2.add_transition(rmLoaderOut2)
        addLoaderOut2 = 'lib.removeOutputArc("line2", "load", 1)'
        loop2.add_transition(addLoaderOut2)
        loop2.add_place('loaderOutRemoved')
        loop2.add_place('loaderOutAdded')
        loop2.add_input_arc('doChanges2', rmLoaderOut2, Value(BlackToken()))
        loop2.add_output_arc(rmLoaderOut2, 'loaderOutRemoved', Value(BlackToken()))
        loop2.add_input_arc('loaderOutRemoved', addLoaderOut2, Value(BlackToken()))
        loop2.add_output_arc(addLoaderOut2, 'loaderOutAdded', Value(BlackToken()))
        rmAssemblerIn2 = 'lib.addInputArc("line1", "assemble", 1)'
        loop2.add_transition(rmAssemblerIn2)
        addAssemblerIn2 = 'lib.removeInputArc("line2", "assemble", 1)'
        loop2.add_transition(addAssemblerIn2)
        loop2.add_place('assemblerInRemoved')
        loop2.add_place('assemblerInAdded')
        loop2.add_input_arc('loaderOutAdded', rmAssemblerIn2, Value(BlackToken()))
        loop2.add_output_arc(rmAssemblerIn2, 'assemblerInRemoved', Value(BlackToken()))
        loop2.add_input_arc('assemblerInRemoved', addAssemblerIn2, Value(BlackToken()))
        loop2.add_output_arc(addAssemblerIn2, 'assemblerInAdded', Value(BlackToken()))
        loop2.add_place('hRemoved2')
        rmHArc2 = 'lib.removeInhibitortArc(p, "load", 1)'
        loop2.add_transition(rmHArc2)
        loop2.add_input_arc('assemblerInAdded', rmHArc2, Value(BlackToken()))
        loop2.add_input_arc('inHIn', rmHArc2, Test(Variable('p')))
        loop2.add_output_arc(rmHArc2, 'hRemoved2', Value(BlackToken()))
        rmFixTr = 'lib.removeTransition("fix")'
        loop2.add_transition(rmFixTr)
        loop2.add_place('fixTrRemoved')
        rmFixArc = 'lib.removeInputArc("broken", "fix", 1)'
        loop2.add_transition(rmFixArc)
        loop2.add_input_arc('hRemoved2', rmFixArc, Value(BlackToken()))
        loop2.add_output_arc(rmFixTr, 'fixTrRemoved', Value(BlackToken()))
        loop2.add_input_arc('fixTrRemoved', rmFixArc, Value(BlackToken()))

        #loop2.draw(LOOP2_DOT, render=True)

        net = AdaptiveNetBuilder(self.emulator)    \
            .add_loop(loop1, ['init'])             \
            .add_loop(loop2, ['init21', 'init22']) \
            .build()

        # token game example

        self.fire_lowLevel(net, 'load')
        assert net.get_marking().get('M')('line1') == 1
        assert net.get_marking().get('M')('line2') == 1
        self.fire_lowLevel(net, 'fail')
        assert net.get_marking().get('M')('broken') == 1
        self.fire_highLevel(net, getTokens)
        assert net.get_marking().get('breakSample') == MultiSet([1])
        self.fire_highLevel(net, 'broken')
        self.fire_highLevel(net, hMult)
        self.fire_highLevel(net, blockLoader)
        assert net.get_marking().get('H')(('load','broken')) == 1
        assert net.get_marking().get('blockedLoader') == MultiSet([BlackToken()])
        self.fire_highLevel(net, detachLoader)
        self.fire_highLevel(net, addLoaderOut)
        assert net.get_marking().get('O')(('load','line1')) == 0
        assert net.get_marking().get('O')(('load','line2')) == 2
        self.fire_lowLevel(net, 'work2')
        self.fire_highLevel(net, getLine2)
        assert net.get_marking().get('line2Pieces') == MultiSet([0])
        self.fire_highLevel(net, getPendings)
        assert net.get_marking().get('pendingPieces') == MultiSet([1])
        self.fire_highLevel(net, 'flush')
        self.fire_highLevel(net, empty)
        self.fire_highLevel(net, add)
        assert net.get_marking().get('M')('line1') == 0
        assert net.get_marking().get('M')('line2') == 1
        self.fire_highLevel(net, getWorked1)
        assert net.get_marking().get('workedPieces') == MultiSet([0])
        self.fire_highLevel(net, 'changeAssembler')
        self.fire_highLevel(net, addInArc)
        self.fire_highLevel(net, rmInArc)
        self.fire_highLevel(net, rmHArc)
        self.fire_highLevel(net, addFixTr)
        self.fire_highLevel(net, addFixArc)
        assert net.get_marking().get('M')('broken') == 1
        assert net.get_marking().get('H')(('assemble', 'worked1')) == 0
        assert net.get_marking().get('T')('fix') == 1
        assert net.get_marking().get('I')(('fix', 'broken')) == 1

    def fire_lowLevel(self, net, transition):
        modes = net.transition('move').modes()
        for m in modes:
            if m('t') == transition:
                mode = m
        assert mode('t') == transition
        net.transition('move').fire(mode)

    def fire_highLevel(self, net, transition):
        modes = net.transition(transition).modes()
        assert len(modes) > 0
        net.transition(transition).fire(modes[0])
