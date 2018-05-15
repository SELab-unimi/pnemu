# PNEmu

PNEmu is an *extensible python library* that provides all the necessary to model **Self-Adaptive Systems** using High-Level Petri nets.
It provides to researchers the ability to quickly model and simulate self-adaptive systems using *P/T nets* and *High-Level Petri nets* as *managed* and *managing* subsystem, respectively.
The *managed* subsystem is encoded into the marking of a High-Level Petri net **emulator** that can
*execute*, *sense* and *alter* the *managed* subsystem by means of library primitives implemented by using *High-Level* net transitions.
Our modeling approach leverages the concept of subnets  to specify decentralized adaptation control in terms of **MAPE** loops.


## How do I get setup?

To install PNEmu you can use:
```
pip3 install pnemu
```
this will download and install the latest release from the [Python Package Index](https://pypi.python.org/pypi).

To install PyRPN from sources, first download the latest version from this repository.
You can either clone the repository or download and uncompress the .zip archive.
Then run:
```
python3 setup.py install
```

PyRPN should work fine with any Python 3.x version.

## First steps with PNEmu

TODO.

## Licence

See the [LICENSE](LICENSE.txt) file for license rights and limitations (GNU GPL-3.0+).

## Who do I talk to?

* Matteo Camilli: matteo.camilli@unimi.it
* Lorenzo Capra: lorenzo.capra@unimi.it
