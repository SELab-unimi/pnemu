from snakes.nets import *
import snakes.plugins
from snakes.pnml import dumps
from pnemu import Emulator, MAPE, PT

REQ = 1 # requests
CAPACITY = 4 # default capacity

# Managed system

pt = PT('PT-net-example')
pt.add_place('requests', REQ)
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
pt.add_inhibitor_arc('ac', 'acS', CAPACITY)
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
pt.add_inhibitor_arc('pay', 'payS', CAPACITY)
pt.add_input_arc('pay', 'payE')
pt.add_output_arc('payE', 'payDone')

pt.add_transition('notify')
pt.add_input_arc('payDone', 'notify')

# Managing system

emulator = Emulator(pt)

# shared knowledge
emulator.add_place('threshold_lower', zone=MAPE.K)
emulator.add_place('threshold_upper', zone=MAPE.K)
emulator.add_place('min_instances', zone=MAPE.K)
emulator.add_place('ac_instance', zone=MAPE.K)
emulator.add_place('pay_instance', zone=MAPE.K)
emulator.add_place('instances', zone=MAPE.K)

# Adaptation concern A (Minimize number of containers)
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
getRunningInstances = 'lib::getTokens(a) := m'
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
emulator.add_output_arc(hMult, 'running', Expression("MultiSet([(t, r)])"))

emulator.add_output_arc('fire', 'initA', Value(True))

emulator.unfold_net()

# Adaptation concern B (Optimize container distribution)

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
modes = net.transition('lib::hMult(p,t) := r').modes()
net.transition('lib::hMult(p,t) := r').fire(modes[0])
