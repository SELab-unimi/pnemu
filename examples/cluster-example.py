from snakes.nets import *
import snakes.plugins
from snakes.pnml import dumps
from pnemu import Emulator, MAPE, PT

LOWER = 4 # lower bound running instances
UPPER = 8 # upper bound running instances
LIMIT = 10 # total available instances

# Managed system

pt = PT('PT-net-example')
pt.add_place('requests', 1)
pt.add_place('acQ')
pt.add_place('ac')
pt.add_place('access')
pt.add_transition('acR')
pt.add_transition('acS')
pt.add_transition('acE')
pt.add_input_arc('requests', 'acR')
pt.add_output_arc('acR', 'acQ')
pt.add_input_arc('acQ', 'acS')
pt.add_output_arc('acS', 'ac')
pt.add_inhibitor_arc('ac', 'acS', LOWER)
pt.add_input_arc('ac', 'acE')
pt.add_output_arc('acE', 'access')

pt.add_transition('payR')

pt.add_place('payQ')
pt.add_place('pay')
pt.add_place('payDone')
pt.add_transition('payS')
pt.add_transition('payE')
pt.add_input_arc('access', 'payR')
pt.add_output_arc('payR', 'payQ')
pt.add_input_arc('payQ', 'payS')
pt.add_output_arc('payS', 'pay')
pt.add_inhibitor_arc('pay', 'payS', LOWER)
pt.add_input_arc('pay', 'payE')
pt.add_output_arc('payE', 'payDone')

pt.add_transition('notify')
pt.add_input_arc('payDone', 'notify')

# Managing system

emulator = Emulator(pt)

# #################
# shared knowledge
# #################
emulator.add_place('thresholdLower', tokens=LOWER, zone=MAPE.K)
emulator.add_place('thresholdUpper', tokens=UPPER, zone=MAPE.K)
emulator.add_place('minInstances', tokens=LOWER, zone=MAPE.K)
emulator.add_place('acInstance', tokens=MultiSet([('ac', 'acS', 1)]), zone=MAPE.K)
emulator.add_place('payInstance', tokens=MultiSet([('pay', 'payS', 1)]), zone=MAPE.K)
emulator.add_place('instances', tokens=2, zone=MAPE.K)

# #################
# Adaptation concern A (Minimize number of containers)
# #################
emulator.add_place('initA', zone=MAPE.M)
emulator.add_place('readyA', tokens=True, zone=MAPE.M)
emulator.add_place('getInstances', zone=MAPE.M)
emulator.add_place('splitP', zone=MAPE.M)
emulator.add_place('splitT', zone=MAPE.M)
emulator.add_place('splitR', tokens=True, zone=MAPE.M)
emulator.add_place('getComputing', zone=MAPE.M)
emulator.add_place('getRequests', zone=MAPE.M)
emulator.add_place('running', zone=MAPE.M)
emulator.add_place('computing', zone=MAPE.M)
emulator.add_place('requestsA', zone=MAPE.M)
emulator.add_place('requestsB', zone=MAPE.M)

hMult = 'lib::hMult(p,t) := r'
getRunningInstances = 'lib::getTokens(a) := x'
getRequests = 'lib::getTokens(e) := n'
emulator.add_transition('startA')
emulator.add_transition(hMult)
emulator.add_transition('split')
emulator.add_transition(getRunningInstances)
emulator.add_transition(getRequests)
emulator.add_transition('pairing')

emulator.add_input_arc('initA', 'startA', Variable('b'))
emulator.add_input_arc('readyA', 'startA', Variable('b'))
emulator.add_output_arc('startA', 'getInstances', Flush("MultiSet([('acS', 'ac'), ('payS', 'pay')])"))
emulator.add_input_arc('getInstances', 'split', Variable('a'))
emulator.add_input_arc('splitR', 'split', Variable('b'))
emulator.add_output_arc('split', 'splitP', Expression('a[1]'))
emulator.add_output_arc('split', 'splitT', Expression('a[0]'))
emulator.add_input_arc('splitP', hMult, Variable('p'))
emulator.add_input_arc('splitT', hMult, Variable('t'))
emulator.add_output_arc(hMult, 'splitR', Value(True))
emulator.add_output_arc(hMult, 'running', Expression("(t, r)"))
emulator.add_output_arc('startA', 'getComputing', Flush("MultiSet(['ac', 'pay'])"))
emulator.add_input_arc('getComputing', getRunningInstances, Variable('a'))
emulator.add_output_arc(getRunningInstances, 'computing', Expression("(a, x)"))
emulator.add_output_arc('startA', 'getRequests', Flush("MultiSet(['acQ', 'payQ'])"))
emulator.add_input_arc('getRequests', getRequests, Variable('e'))
emulator.add_output_arc(getRequests, 'requestsA', Expression("(e, n)"))
emulator.add_output_arc(getRequests, 'requestsB', Expression("(e, n)"))

emulator.add_place('runningBis', zone=MAPE.A)
emulator.add_place('computingBis', zone=MAPE.A)
emulator.add_place('requestsABis', zone=MAPE.A)
emulator.add_place('feasibleReq', zone=MAPE.A)
emulator.add_place('decReq', zone=MAPE.A)

emulator.add_transition('runningCross1', Expression("e[0] == 'acS'"))
emulator.add_transition('runningCross2', Expression("e[0] == 'payS'"))
emulator.add_transition('computingCross1', Expression("e[0] == 'ac'"))
emulator.add_transition('computingCross2', Expression("e[0] == 'pay'"))
emulator.add_transition('requestsCross')
emulator.add_transition('isFeasible', Expression("i[0] == c[0]"))
emulator.add_transition('isDec')

emulator.add_input_arc('running', 'runningCross1', Variable('e'))
emulator.add_input_arc('running', 'runningCross2', Variable('e'))
emulator.add_output_arc('runningCross1', 'runningBis', Expression("('acQ', e[1])"))
emulator.add_output_arc('runningCross2', 'runningBis', Expression("('payQ', e[1])"))
emulator.add_input_arc('computing', 'computingCross1', Variable('e'))
emulator.add_input_arc('computing', 'computingCross2', Variable('e'))
emulator.add_output_arc('computingCross1', 'computingBis', Expression("('acQ', e[1])"))
emulator.add_output_arc('computingCross2', 'computingBis', Expression("('payQ', e[1])"))
emulator.add_input_arc('requestsA', 'requestsCross', Variable('e'))
emulator.add_output_arc('requestsCross', 'requestsABis', Variable('e'))
emulator.add_input_arc('runningBis', 'isFeasible', Variable('i'))
emulator.add_input_arc('computingBis', 'isFeasible', Variable('c'))
emulator.add_input_arc('minInstances', 'isFeasible', Variable('m'))
emulator.add_output_arc('isFeasible', 'minInstances', Variable('m'))
emulator.add_output_arc('isFeasible', 'feasibleReq', Expression("(i[0], i[1]<c[1] and i[1]>m)"))
emulator.add_input_arc('requestsABis', 'isDec', Variable('e'))
emulator.add_input_arc('thresholdLower', 'isDec', Variable('t'))
emulator.add_output_arc('isDec', 'thresholdLower', Variable('t'))
emulator.add_output_arc('isDec', 'decReq', Expression("(e[0], e[1]<t)"))

emulator.add_place('feasibleReqBis', zone=MAPE.P)
emulator.add_place('decReqBis', zone=MAPE.P)
emulator.add_place('dec', zone=MAPE.P)
emulator.add_place('reqAHandled', zone=MAPE.P)

emulator.add_transition('feasibleReqCross')
emulator.add_transition('decReqCross')
emulator.add_transition('confirmDec', Expression('e[1] and f[1]'))
emulator.add_transition('negateDec', Expression('not e[1] or not f[1]'))

emulator.add_input_arc('feasibleReq', 'feasibleReqCross', Variable('e'))
emulator.add_output_arc('feasibleReqCross', 'feasibleReqBis', Variable('e'))
emulator.add_input_arc('decReq', 'decReqCross', Variable('e'))
emulator.add_output_arc('decReqCross', 'decReqBis', Variable('e'))
emulator.add_input_arc('feasibleReqBis', 'confirmDec', Variable('f'))
emulator.add_input_arc('feasibleReqBis', 'negateDec', Variable('f'))
emulator.add_input_arc('decReqBis', 'confirmDec', Variable('e'))
emulator.add_input_arc('decReqBis', 'negateDec', Variable('e'))
emulator.add_output_arc('confirmDec', 'dec', Expression('e[0]'))
emulator.add_output_arc('negateDec', 'reqAHandled', Expression('e[0]'))

emulator.add_place('instance', zone=MAPE.E)
emulator.add_place('splitBisR', tokens=True, zone=MAPE.E)
emulator.add_place('splitBisP', zone=MAPE.E)
emulator.add_place('splitBisT', zone=MAPE.E)
emulator.add_place('splitBisN', zone=MAPE.E)

removeH = 'lib::removeInhibitorArc(p,t,n)'
emulator.add_transition('instanceCross1', Expression("e == 'payS'"))
emulator.add_transition('instanceCross2', Expression("e == 'acS'"))
emulator.add_transition('splitBis')
emulator.add_transition(removeH)
emulator.add_transition('getReady', Expression('len(r)>=2'))

emulator.add_input_arc('dec', 'instanceCross1', Variable('e'))
emulator.add_input_arc('payInstance', 'instanceCross1', Variable('a'))
emulator.add_output_arc('instanceCross1', 'payInstance', Variable('a'))
emulator.add_input_arc('dec', 'instanceCross2', Variable('e'))
emulator.add_input_arc('acInstance', 'instanceCross2', Variable('a'))
emulator.add_output_arc('instanceCross2', 'acInstance', Variable('a'))
emulator.add_output_arc('instanceCross1', 'instance', Variable('a'))
emulator.add_output_arc('instanceCross2', 'instance', Variable('a'))
emulator.add_input_arc('instance', 'splitBis', Variable('a'))
emulator.add_input_arc('splitBisR', 'splitBis', Variable('r'))
emulator.add_output_arc('splitBis', 'splitBisP', Expression('a[0]'))
emulator.add_output_arc('splitBis', 'splitBisT', Expression('a[1]'))
emulator.add_output_arc('splitBis', 'splitBisN', Expression('a[2]'))
emulator.add_input_arc('splitBisP', removeH, Variable('p'))
emulator.add_input_arc('splitBisT', removeH, Variable('t'))
emulator.add_input_arc('splitBisN', removeH, Variable('n'))
emulator.add_output_arc(removeH, 'splitBisR', Value(True))
emulator.add_output_arc(removeH, 'reqAHandled', Variable('p'))
emulator.add_input_arc('reqAHandled', 'getReady', Flush('r'))
emulator.add_output_arc('getReady', 'readyA', Value(True))


emulator.add_output_arc('fire', 'initA', Value(True))


# #################
# Adaptation concern B (Optimize container distribution)
# #################



emulator.unfold_net()
net = emulator.get_net()

# f = open('model.pnml', 'w')
# f.write(dumps(net))
# f.close()

emulator.draw_pt(dot_file='managed.dot')
emulator.draw(dot_file='managing.dot')

# execution example

modes = net.transition('fire').modes()
net.transition('fire').fire(modes[0])
modes = net.transition('startA').modes()
net.transition('startA').fire(modes[0])
modes = net.transition('split').modes()
net.transition('split').fire(modes[0])
modes = net.transition(hMult).modes()
net.transition(hMult).fire(modes[0])
modes = net.transition(getRunningInstances).modes()
net.transition(getRunningInstances).fire(modes[0])
modes = net.transition(getRunningInstances).modes()
net.transition(getRunningInstances).fire(modes[0])
modes = net.transition(getRequests).modes()
net.transition(getRequests).fire(modes[0])
modes = net.transition(getRequests).modes()
net.transition(getRequests).fire(modes[0])

modes = net.transition('runningCross1').modes()
net.transition('runningCross1').fire(modes[0])
net.get_marking().get('runningBis')
MultiSet([('acQ', 4)])
net.transition('computingCross1').modes()
[Substitution(e=('ac', 0))]
modes = net.transition('computingCross1').modes()
net.transition('computingCross1').fire(modes[0])
modes = net.transition('requestsCross').modes()
net.transition('requestsCross').fire(modes[0])
modes = net.transition('isDec').modes()
net.transition('isDec').fire(modes[0])
net.get_marking().get('feasibleReq')
modes = net.transition('isFeasible').modes()
net.get_marking().get('feasibleReq')
net.transition('isFeasible').fire(modes[0])

modes = net.transition('feasibleReqCross').modes()
net.transition('feasibleReqCross').fire(modes[0])
modes = net.transition('decReqCross').modes()
net.transition('decReqCross').fire(modes[0])
modes = net.transition('negateDec').modes()
net.transition('negateDec').fire(modes[0])
