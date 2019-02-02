# PNEmu

PNEmu is an *extensible python library* that provides all the necessary to model **Self-Adaptive Systems** using High-Level Petri nets (HLPNs).
It provides to researchers the ability to quickly model and simulate self-adaptive systems using *P/T nets* and *High-Level Petri nets* as *managed* and *managing* subsystem, respectively.
The *managed* subsystem is encoded into the marking of a High-Level Petri net **emulator** that can
*execute*, *sense* and *alter* the *managed* subsystem by means of library primitives.
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
from pnemu import FeedbackLoop
loop1 = FeedbackLoop('fault-tolerance')
loop1.add_place('init')
loop1.add_place('breakSample')
getTokens = 'lib.getTokens("broken")->n'
loop1.add_transition(getTokens)
loop1.add_input_arc('init', getTokens, Value(BlackToken()))
loop1.add_output_arc(getTokens, 'breakSample', Variable('n'))
...
loop1.draw('resources/loop1.dot', render=True)
```

The `lib.getTokens` represents a (read) primitive that allows the base layer to be sampled.
Namely, it reads the number of tokens inside the place passed as argument (either "in place" or attached to an input arc variable).

All the read/write primitives are defined and documented inside the `primitives.py` module.
Each primitive is defined as a net transition attached to specific elements of the *emulator*.
An example of primitive definition follows.

```python
entry = LibEntry(
    signature='lib.getTokens(p_) -> M(p_)',
    places=[Place('M')],
    input=[('M', signature, Flush('M'))],
    output=[('M', signature, Flush('M'))])
```

Once all the loops have been defined the entire self-adaptive system can be built by using the `AdaptiveNetBuilder`.

```python
net = AdaptiveNetBuilder(emulator)          \
        .add_loop(loop1, ['init'], ['fail'])    \
        .add_loop(loop2, ['init2'], ['repair']) \
        .build()
```

An example of interactive simulation (through token game) follows below.

```python
self.fire_lowLevel(net, 'load')
assert net.get_marking().get('M')('line1') == 1
assert net.get_marking().get('M')('line2') == 1
self.fire_lowLevel(net, 'fail')
assert net.get_marking().get('M')('broken') == 1
self.fire_highLevel(net, blockLoader)
assert net.get_marking().get('H')(('load','broken')) == 1
assert net.get_marking().get('locked') == MultiSet([BlackToken()])
...
```

The complete example can be found inside the `test_ms.py` file.
The execution of the test suite requires the [pytest](https://docs.pytest.org/en/latest/) framework.
To run all the tests just type:

```
make test
```

## Model checking

Since the the `AdaptiveNetBuilder` creates a `snakes.nets.Petrinet` object, it is possible to use
the [neco-net-compiler](https://github.com/Lvyn/neco-net-compiler) along with the [SPOT](https://spot.lrde.epita.fr/) library
to verify the correctness of the overall self-adaptive system with respect to design-time requirements
expressed using LTL properties.
Once both the `spot` library and the `neco-net-compiler` have been installed, it is possible to compile the
[adaptive manufacturing system](examples/ms-example.py) example by using the following command.

```
neco-compile -m ms-example.py -lcython --import pnemu.functions
```

Once the model has been successfully compiled, it is possible to compile and then verify the desired LTL properties,
for instance:

```
neco-check --formula="G (not deadlock)"
neco-spot neco_formula
```

In this simple example, we check whether it is possible to loose the raw pieces along the production process.

## Licence

See the [LICENSE](LICENSE.txt) file for license rights and limitations (GNU GPL-3.0+).

## External references

* The [SNAKES](https://snakes.ibisc.univ-evry.fr/) library;
* [PNemu](https://snakes.ibisc.univ-evry.fr/articles/related-tools.html) as a representative example of SNAKES usage;
* [neco-net-compiler](https://code.google.com/archive/p/neco-net-compiler/wikis/UsingNecoCLI.wiki) usage and examples.

## How do I cite PNemu?

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
