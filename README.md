# PNEmu

PNEmu is an *extensible python library* that provides all the necessary to model **Self-Adaptive Systems** using High-Level Petri nets (HLPNs).
It provides to researchers the ability to quickly model and simulate self-adaptive systems using *P/T nets* and *High-Level Petri nets* as *managed* and *managing* subsystem, respectively.
The *managed* subsystem is encoded into the marking of a High-Level Petri net **emulator** that can
*execute*, *sense* and *alter* the *managed* subsystem by means of library primitives implemented by using *High-Level* net transitions.
Our modeling approach leverages High-Level Petri to specify decentralized adaptation control in terms of feedback loops.


## How do I get setup?

To install PyRPN from sources, first download the latest version from this repository.
You can either clone the repository or download and uncompress the .zip archive.
Then run:
```
python3 setup.py install
```

PyRPN should work fine with any Python 3.x version.

## First steps with PNEmu

Let's start by defining a Place/Transition (P/T) net that represents the *base layer*.

The code snippets reported in the following loads the `ms.pnml` file (i.e., a manufacturing system example),
in the `resources` directory.
The `PT` object is used in turn to initialize the *emulator* component.
The *emulator* is the fundamental building block that allows the base layer to be represented as data inside the marking of a HLPN.


```python
from snakes.nets import *
from pnemu import PT, Emulator

pt = PT('ms', 'resources/ms.pnml')
pt.export_dot('resources/ms.dot')
emulator = Emulator(pt)
```
The snippet can be executed as script or in a interactive Python shell.


Once the base-level has been defined we can create the *managing layer*.
The managing layer is composed of a number feedback loops (one for each adaptation concern), given in terms of HLPNs.


```python
loop1 = FeedbackLoop('fault-tolerance')
loop1.add_place('init')
loop1.add_place('breakSample')
getTokens = 'lib.getTokens("broken") := n'
loop1.add_transition(getTokens)
loop1.add_input_arc('init', getTokens, Value(BlackToken()))
loop1.add_output_arc(getTokens, 'breakSample', Variable('n'))
...
...
```

The `lib.getTokens` represents a (read) primitive that allows to sample the base layer.
Namely, it reads the number of tokens inside the place passed as argument (either "in place" or attached to an input arc variable).

All the read/write primitives are defined and documented inside the `primitives.py` module.
Each primitive is defined as a transition attached to specific elements of the *emulator*.

```python
entry = LibEntry(
    signature='lib.getTokens(p_) := M(p_)'',
    places=[Place('M')],
    input=[('M', signature, Test(Flush('M')))],
    output=[])
```

Once all the loops have been defined the entire self-adaptive system can be built by using the `AdaptiveNetBuilder`.

```python
net = AdaptiveNetBuilder(self.emulator)  \
  .add_loop(loop1, ['init'])             \
  .add_loop(loop2, ['init21', 'init22']) \
  .build()
```

An example of interactive simulation (through token game) follows below.

```python
self.fire_lowLevel(net, 'load')
assert net.get_marking().get('M')('line1') == 1
assert net.get_marking().get('M')('line2') == 1
self.fire_lowLevel(net, 'fail')
assert net.get_marking().get('M')('broken') == 1
self.fire_highLevel(net, getTokens)
assert net.get_marking().get('breakSample') == MultiSet([1])
...
```

The complete example can be found inside the `test_ms.py` file.

## Licence

See the [LICENSE](LICENSE.txt) file for license rights and limitations (GNU GPL-3.0+).

## External references

* The [SNAKES](https://snakes.ibisc.univ-evry.fr/) library
* [PNemu](https://snakes.ibisc.univ-evry.fr/articles/related-tools.html) as a representative example of SNAKES usage

**How do I cite PNemu?**

Matteo Camilli, Carlo Bellettini, and Lorenzo Capra. 2018. A high-level petri net-based formal model of distributed self-adaptive systems. In Proceedings of the 12th European Conference on Software Architecture: Companion Proceedings (ECSA '18). ACM, New York, NY, USA, Article 40, 7 pages. DOI: https://doi.org/10.1145/3241403.3241445

**Bibtex**
```
@inproceedings{Camilli:2018:HPN:3241403.3241445,
 author = {Camilli, Matteo and Bellettini, Carlo and Capra, Lorenzo},
 title = {A High-level Petri Net-based Formal Model of Distributed Self-adaptive Systems},
 booktitle = {Proceedings of the 12th European Conference on Software Architecture: Companion Proceedings},
 series = {ECSA '18},
 year = {2018},
 isbn = {978-1-4503-6483-6},
 location = {Madrid, Spain},
 pages = {40:1--40:7},
 articleno = {40},
 numpages = {7},
 url = {http://doi.acm.org/10.1145/3241403.3241445},
 doi = {10.1145/3241403.3241445},
 acmid = {3241445},
 publisher = {ACM},
 address = {New York, NY, USA},
 keywords = {MAPE-K loop, distributed systems, formal modeling, formal verification, high-level petri nets, self-adaptation},
}
```

## Who do I talk to?

* Matteo Camilli: matteo.camilli@unimi.it
* Lorenzo Capra: lorenzo.capra@unimi.it
