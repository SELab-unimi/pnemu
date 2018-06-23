# PNEmu

PNEmu is an *extensible python library* that provides all the necessary to model **Self-Adaptive Systems** using High-Level Petri nets.
It provides to researchers the ability to quickly model and simulate self-adaptive systems using *P/T nets* and *High-Level Petri nets* as *managed* and *managing* subsystem, respectively.
The *managed* subsystem is encoded into the marking of a High-Level Petri net **emulator** that can
*execute*, *sense* and *alter* the *managed* subsystem by means of library primitives implemented by using *High-Level* net transitions.
Our modeling approach leverages the concept of subnets  to specify decentralized adaptation control in terms of **MAPE** loops.


## How do I get setup?

To install PyRPN from sources, first download the latest version from this repository.
You can either clone the repository or download and uncompress the .zip archive.
Then run:
```
python3 setup.py install
```

PyRPN should work fine with any Python 3.x version.

## First steps with PNEmu

Let's start by defining a simple Place/Transition (P/T) net that represents the *base-level*.

The code snippets reported in the following are taken from the `cluster-example` file,
in the `examples` directory.
Code snippets can be executed as script or in a interactive Python shell.

```python
from snakes.nets import *
from pnemu import Emulator, MAPE, PT

base = PT('base-example')
pt.add_place('requests', 1)
pt.add_place('acQ')
pt.add_place('ac')
...
pt.add_transition('acR')
pt.add_transition('acS')
pt.add_transition('acE')
...
pt.add_inhibitor_arc('ac', 'acS', LOWER)
pt.add_input_arc('ac', 'acE')
pt.add_output_arc('acE', 'access')
...
```

To visualize the base-level model we can export the `.dot` file as follows.

```python
base.export_dot(dot_file='examples/base-example.dot')
```

Once the base-level has been defined we can create the managing subsystem.
We can create places/transitions/arcs and add them to specific MAPE components, as follows.

```python
emulator = Emulator(pt)
# shared knowledge
emulator.add_place('thresholdLower', tokens=LOWER, zone=MAPE.K)
emulator.add_place('thresholdUpper', tokens=UPPER, zone=MAPE.K)
# monitor
emulator.add_place('initA', zone=MAPE.M)
emulator.add_place('readyA', tokens=True, zone=MAPE.M)
emulator.add_place('getInstances', zone=MAPE.M)
...
```

An example of API primitive instance follows below.
Here, we use the `hMult` API primitive to realize a specific *sensor* to sample the number of allocated resources to a specific service.

```python
emulator.add_transition('startA')
hMult = 'lib::hMult(p,t) := r'
emulator.add_transition(hMult)
emulator.add_input_arc('splitP', hMult, Variable('p'))
emulator.add_input_arc('splitT', hMult, Variable('t'))
emulator.add_output_arc(hMult, 'splitR', Value(True))
emulator.add_output_arc(hMult, 'running', Expression("(t, r)"))
...
```

To visualize the overall system we can export model in `.dot` format as follows.

```python
net = emulator.get_net()
emulator.draw(dot_file='managing.dot')
```

An example of interactive simulation follows below.

```python
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
...
```


## Licence

See the [LICENSE](LICENSE.txt) file for license rights and limitations (GNU GPL-3.0+).

## Who do I talk to?

* Matteo Camilli: matteo.camilli@unimi.it
* Lorenzo Capra: lorenzo.capra@unimi.it
