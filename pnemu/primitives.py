from snakes.nets import *

LIB_PREFIX = 'lib.'
FLUSH = 'flush'
ASSIGNMENT = ':='
ARG_SEPARATOR = ','
RESULT_SEPARATOR = ';'

class LibEntry:

    def __init__(self, signature, places, input_arcs, output_arcs, guard=None):
        self.signature = signature
        self.places = places
        self.input_arcs = input_arcs
        self.output_arcs = output_arcs
        self.guard = guard

        @property
        def signature(self):
            return self.__signature

        @signature.setter
        def signature(self, signature):
            self.__signature = signature

        @property
        def places(self):
            return self.__places

        @places.setter
        def places(self, places):
            self.__places = places

        @property
        def guard(self):
            return self.__guard

        @guard.setter
        def guard(self, guard):
            self.__guard = guard

        @property
        def input_arcs(self):
            return self.__input_arcs

        @input_arcs.setter
        def input_arcs(self, arcs):
            self.__input_arcs = arcs

        @property
        def output_arcs(self):
            return self.__output_arcs

        @output_arcs.setter
        def output_arcs(self, arcs):
            self.__output_arcs = arcs


# Utility functions

def function_name(call_str):
    """Return the lib function name, given the user defined transition name.
    e.g., function_name('lib::getMarking(p) := n') = 'lib::getMarking' """
    return call_str[:call_str.find('(')]

# Utility functions used to implement the unfolding

def function_name(call_str):
    """Return the lib function name, given the user defined transition name.
    e.g., function_name('lib::getMarking(p) := n') = 'lib::getMarking' """
    return call_str[:call_str.find('(')]

def function_in(strFunct):
    """Return the list of input variables, given a function signature.
    e.g., function_in('lib::name(a, b, foo("str")) := n') = ['a', 'b', 'foo("str")'] """
    if('=' in strFunct):
        tmp = strFunct[strFunct.find('(')+1:strFunct.find('=')]
    else:
        tmp = strFunct[strFunct.find('(')+1:]
    args = tmp[:tmp.rfind(')')]
    result = [v.strip() for v in args.split(ARG_SEPARATOR)]
    if result == ['']:
        return []
    else:
        return result

def function_out(strFunct):
    """Return the list of output variables/expressions, given a function signature.
    e.g., function_out('lib::name(a_, b_) := foo(a_, b_); bar(b_)') = ['foo(a_, b_)', 'bar(b_)'] """
    result = [v.strip() for v in strFunct[strFunct.find(ASSIGNMENT)+len(ASSIGNMENT):].split(RESULT_SEPARATOR)]
    if result == ['']:
        return []
    else:
        return result


# CORE LIB (read) usage
# `lib::getTokens(p) := n` given a PTPlace as input var `p`, it returns a natural number (>= 0) into var `n`
# `lib::getMarking() := m` returns a multiset of PTPlace into var `m` (multiplicity represents the number of tokens)
# `lib::getPlaces() := p` returns a multiset of PTPlace `p`
# `lib::getPlacesStartingWith(s) := e` returns a multiset `e` of PTPlaces, whose name start with the prefix `s`
# `lib::getTransitions() := t` returns a multiset of PTTransition in var `t`
# `lib::getTransitionsStartingWith(s) := e` returns a multiset `e` of PTTransitions, whose name start with the prefix `s`
# `lib::exists(e) := v`: returns True in var `v` iff the element (either a PTPlace or a PTTransition) in var `e` exists
# `lib::pre(e) := r` given an element (either a PTPlace or a PTTransition) in var `e`, it returns a multiset of PTPlace/PTTransition belonging to the preset of `e` (multiplicity represents the arc weight)
# `lib::post(e) := r` given an element (either a PTPlace or a PTTransition) in var `e`, it returns a multiset of PTPlace/PTTransition belonging to the postset of `e` (multiplicity represents the arc weight)
# `lib::inh(e) := r`: given an element (either a PTPlace or a PTTransition) in var `e`, it returns a multiset of PTPlace/PTTransition s.t. the element `e` inhibits/is-inhibitor of (multiplicity represents the arc weight)
# `lib::iMult(p,t) := n`: givent a PTPlace `p` and a PTTransition `t`, it returns the multiplicity of the input arc (p,t)
# `lib::hMult(p,t) := n`: givent a PTPlace `p` and a PTTransition `t`, it returns the multiplicity of the inhibitor arc (p,t)
# `lib::oMult(t,p) := n`: givent a PTTransition `t` and a PTPlace `p`, it returns the multiplicity of the output arc (t,p)

# ASSUMPTION
# the user uses lowercase letters for variables (e.g., p, t, h)
# uppercase letters (e.g., M, I, H, ...) and lowercase letters followed by `_` (e.g., p_, i_, h_) are reserved names

READ_LIB = { }
signature = LIB_PREFIX + "getTokens(p_) := M(p_)"
entry = LibEntry(
    signature,
    [Place('M')],
    [('M', signature, Test(Flush('M')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getMarking() := M"
entry = LibEntry(
    signature,
    [Place('M')],
    [('M', signature, Test(Flush('M')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getPlaces() := P"
entry = LibEntry(
    signature,
    [Place('P')],
    [('P', signature, Test(Flush('P')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getPlacesStartingWith(s_) := filter(P,s_)"
entry = LibEntry(
    signature,
    [Place('P')],
    [('P', signature, Test(Flush('P')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getTransitions() := T"
entry = LibEntry(
    signature,
    [Place('T')],
    [('T', signature, Test(Flush('T')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getTransitionsStartingWith(s_) := filter(T,s_)"
entry = LibEntry(
    signature,
    [Place('T')],
    [('T', signature, Test(Flush('T')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "exists(e_) := P(e_)>0 or T(e_)>0"
entry = LibEntry(
    signature,
    [Place('P'), Place('T')],
    [('P', signature, Test(Flush('P'))), ('T', signature, Test(Flush('T')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "pre(e_) := values(I, e_) + keys(O, e_)"
entry = LibEntry(
    signature,
    [Place('I'), Place('O')],
    [('I', signature, Test(Flush('I'))), ('O', signature, Test(Flush('O')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "post(e_) := values(O, e_) + keys(I, e_)"
entry = LibEntry(
    signature,
    [Place('I'), Place('O')],
    [('I', signature, Test(Flush('I'))), ('O', signature, Test(Flush('O')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "inh(e_) := values(H, e_) + keys(H, e_)"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Test(Flush('H')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "hMult(p_,t_) := H((t_, p_))"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Test(Flush('H')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "iMult(p_,t_) := I((t_, p_))"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Test(Flush('I')))],
    [])
READ_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "oMult(t_,p_) := O((t_, p_))"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Test(Flush('O')))],
    [])
READ_LIB.update({function_name(signature) : entry})

# CORE LIB (write) usage
# `lib::addPlace(p)` it adds the PTPlace contained in var `p` into the reifiction place `P`
# `lib::addTransition(t)` it adds the PTTransition contained in var `t` into the reifiction place `T`
# `lib::setTokens(p, n)` given a PTPlace (`p` var) and a number (`n` var), it mofifies the marking of the reification place `M` by setting the number of tokens in `p` to `n`
# `lib::addInputArc(p, t, n)` given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it adds an input arc (p, t) with multiplicity n into the place `I` of the reification
# `lib::addOutputArc(p, t, n)` given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it adds an output arc (p, t) with multiplicity n into the place `O` of the reification
# `lib::addInhibitorArc(p, t, n)` given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it adds an inhibitor arc (p, t) with multiplicity n into the place `H` of the reification
# `lib::removePlace(p)` given a PTPlace (`p` var), it removes the place p from `P` of the reification (it also removes connected arcs)
# `lib::removeTransition(t)` given a PTTransition (`t` var), it removes the transition t from `T` of the reification (it also removes connected arcs)
# `lib::removeInputArc(p, t, n)`given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it reduces the multiplicity of the input arc (p, t) by n, in `I` of the reification
# `lib::removeOutputArc(p, t, n)`given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it reduces the multiplicity of the output arc (p, t) by n, in `O` of the reification
# `lib::removeInhibitorArc(p, t, n)`given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it reduces the multiplicity of the inhibitor arc (p, t) by n, in `H` of the reification
# `lib::setInputArcMult(p, t, n)`given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it sets the multiplicity of the input arc (p, t) to n, in `I` of the reification
# `lib::setOutputArcMult(p, t, n)`given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it sets the multiplicity of the input arc (p, t) to n, in `O` of the reification
# `lib::setInhibitorArcMult(p, t, n)`given a PTPlace (`p` var), a PTTransition (`t` var) and a number (`n` var), it sets the multiplicity of the input arc (p, t) to n, in `H` of the reification

# ASSUMPTION
# the user uses lowercase letters for variables (e.g., p, t, h)
# uppercase letters (e.g., M, I, H, ...) and lowercase letters followed by `_` (e.g., p_, i_, h_) are reserved names

WRITE_LIB = { }
signature = LIB_PREFIX + "addPlace(p_)"
entry = LibEntry(
    signature,
    [Place('P')],
    [],
    [('P', signature, Variable('p_'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addTransition(t_)"
entry = LibEntry(
    signature,
    [Place('T')],
    [],
    [('T', signature, Variable('t_'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "setTokens(p_, n_)"
entry = LibEntry(
    signature,
    [Place('M')],
    [('M', signature, Flush('M'))],
    [('M', signature, Flush('setMultiplicity(M, p_, n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addInputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Flush('I'))],
    [('I', signature, Flush('I + MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addOutputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Flush('O'))],
    [('O', signature, Flush('O + MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addInhibitorArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('H'))],
    [('H', signature, Flush('H + MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removePlace(p_)"
entry = LibEntry(
    signature,
    [Place('P'), Place('I'), Place('O'), Place('H'), Place('M')],
    [('P', signature, Flush('P')), ('I', signature, Flush('I')), ('O', signature, Flush('O')), ('H', signature, Flush('H')), ('M', signature, Flush('M'))],
    [('P', signature, Flush('P - MultiSet([p_])')), ('I', signature, Flush('I - filterByValue(I, p_)')), ('O', signature, Flush('O - filterByValue(O, p_)')), ('H', signature, Flush('H - filterByValue(H, p_)')), ('M', signature, Flush('M - MultiSet([p_] * M(p_))'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeTransition(t_)"
entry = LibEntry(
    signature,
    [Place('T'), Place('I'), Place('O'), Place('H')],
    [('T', signature, Flush('T')), ('I', signature, Flush('I')), ('O', signature, Flush('O')), ('H', signature, Flush('H'))],
    [('T', signature, Flush('T - MultiSet([t_])')), ('I', signature, Flush('I - filterByKey(I, t_)')), ('O', signature, Flush('O - filterByKey(O, t_)')), ('H', signature, Flush('H - filterByKey(H, t_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeInputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Flush('I'))],
    [('I', signature, Flush('I - MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeOutputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Flush('O'))],
    [('O', signature, Flush('O - MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeInhibitorArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('H'))],
    [('H', signature, Flush('H - MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "setInputArcMult(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Flush('I'))],
    [('I', signature, Flush('I - MultiSet([(t_, p_)] * I((t_, p_))) + MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "setOutputArcMult(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Flush('O'))],
    [('O', signature, Flush('O - MultiSet([(t_, p_)] * O((t_, p_))) + MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "setInhibitorArcMult(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('H'))],
    [('H', signature, Flush('H - MultiSet([(t_, p_)] * H((t_, p_))) + MultiSet([(t_, p_)] * n_)'))])
WRITE_LIB.update({function_name(signature) : entry})
