from snakes.nets import *
import snakes.plugins
from snakes.pnml import dumps
from pnemu import Emulator, PT

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

emulator.add_place('init')
emulator.add_place('result')
signature = 'lib::getTokens(p) := n'
emulator.add_transition(signature)
emulator.add_output_arc('fire', 'init', Value('p2'))
emulator.add_input_arc('init', signature, Variable('p'))
emulator.add_output_arc(signature, 'result', Variable('n'))
emulator.unfold_net()
net = emulator.get_net()

# f = open('model.pnml', 'w')
# f.write(dumps(net))
# f.close()

emulator.draw_pt(dot_file='managed.dot')
emulator.draw(dot_file='managing.dot')
