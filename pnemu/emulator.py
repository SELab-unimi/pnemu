from snakes.nets import *
import snakes.plugins
from snakes.pnml import dumps, loads
from xml.dom import minidom
import xml.etree.ElementTree as ET
from graphviz import Digraph
from enum import Enum

from .functions import keys, values, intersection

LIB_PREFIX = 'lib::'
FLUSH = 'flush'
ASSIGNMENT = ':='
ARG_SEPARATOR = ','
RESULT_SEPARATOR = ';'

class MAPE(Enum):
    NONE = 0
    M = 1 # MONITOR
    A = 2 # ANALYZE
    P = 3 # PLAN
    E = 4 # EXECUTE
    K = 5 # KNOWLEDGE


class Emulator:

    def __init__(self, pt_net=None, functions=None, concur=True):
        self.net = PetriNet('emulator')

        # basic components
        self.m = Place('M')
        self.o = Place('O')
        self.i = Place('I')
        self.h = Place('H')
        self.t = Place('T')
        self.p = Place('P')
        self.net.add_place(self.m)
        self.net.add_place(self.o)
        self.net.add_place(self.i)
        self.net.add_place(self.h)
        self.net.add_place(self.t)
        self.net.add_place(self.p)

        # `fire` transition for P/T emulation
        self.net.add_transition(Transition('fire', Expression('value(i, t) <= m and (len(value(h, t))==0 or value(h, t) > projection(m, value(h, t)))')))

        # arcs connecting basic components and the `fire` transition
        self.net.add_input('O', 'fire', Flush('o'))
        self.net.add_output('O', 'fire', Flush('o'))
        self.net.add_input('I', 'fire', Flush('i'))
        self.net.add_output('I', 'fire', Flush('i'))
        self.net.add_input('H', 'fire', Flush('h'))
        self.net.add_output('H', 'fire', Flush('h'))
        self.net.add_input('T', 'fire', Variable('t'))
        self.net.add_output('T', 'fire', Variable('t'))
        self.net.add_input('M', 'fire', Flush('m'))
        self.net.add_output('M', 'fire', Flush('m - value(i, t) + value(o, t)'))

        if not concur:
            self.net.add_place(Place('firable', True))
            self.net.add_input('firable', 'fire', Variable('b'))

        # import functions attached to arcs/transitions
        self.net.globals.declare('from pnemu.functions import *')
        #self.net.globals.declare('import math')
        # Extension point: import a collection of custom python-functions to be used in user-defined core lib functions
        if functions is not None:
            self.net.globals.declare("from " + functions + " import *")

        self.core_lib = CORE_LIB

        self.zones = { }

        if pt_net is not None:
            # P/T net encoding
            for p in pt_net.get_places():
                self.p.add(MultiSet([p]))
            for t in pt_net.get_transitions():
                self.t.add(MultiSet([t]))
            for p in pt_net.get_marking():
                self.m.add(MultiSet([p] * pt_net.get_marking().get(p)))
            for t in pt_net.get_input_arcs():
                for arc in pt_net.get_input_arcs().get(t):
                    self.i.add(MultiSet([(arc.dst, arc.src)] * arc.weight))
            for t in pt_net.get_output_arcs():
                for arc in pt_net.get_output_arcs().get(t):
                    self.o.add(MultiSet([(arc.src, arc.dst)] * arc.weight))
            for t in pt_net.get_inhibitor_arcs():
                for arc in pt_net.get_inhibitor_arcs().get(t):
                    self.h.add(MultiSet([(arc.dst, arc.src)] * arc.weight))

    def add_place(self, place, tokens=None, zone=MAPE.NONE):
        p = Place(place)
        if tokens is not None:
            p.add(tokens)
        self.net.add_place(p)
        if zone != MAPE.NONE:
            self.zones.update({place : zone})

    def add_transition(self, transition, guard=None):
        self.net.add_transition(Transition(transition, guard))

    def add_input_arc(self, place, transition, inscription):
        self.net.add_input(place, transition, inscription)

    def add_output_arc(self, transition, place, inscription):
        self.net.add_output(place, transition, inscription)

    def get_transition(self, transition_name):
        return self.net.transition(transition_name)

    def get_input(self, transition_name):
        return self.net.transition(transition_name).input()

    def get_output(self, transition_name):
        return self.net.transition(transition_name).output()

    def get_marking(self):
        return self.net.get_marking()

    def get_net(self):
        return self.net

    def modes(self, tr='fire'):
        return self.net.transition(tr).modes()

    def fire(self, mode, tr='fire'):
        self.net.transition(tr).fire(mode)

    def enabled_pt_transitions(self):
        result = []
        for mode in self.modes():
            result.append(mode.dict().get('t'))
        return result

    def fire_pt(self, transition):
        for mode in self.modes():
            if mode.dict().get('t') == transition:
                self.fire(mode)
                break

    def add_coreFunction(self, signature, entry):
        """Extension point: add a user defined core lib function"""
        self.core_lib.update({function_name(signature) : entry})

    def unfold_net(self):
        """Unfold all the lib:: transitions"""
        for t in self.net.transition():
            if t.name.startswith(LIB_PREFIX) and self.core_lib.get(function_name(t.name)) is not None:
                self.unfold(t, self.core_lib.get(function_name(t.name)))

    def unfold(self, transition, entry):
        """Unfold the input `transition` with the core-lib `entry`"""
        # self.stash(transition)
        for p in entry.places:
            if not self.net.has_place(p.name):
                if self.reification.get_place(p) is not None:
                    self.net.add_place(self.reification.get_place(p))
                else:
                    self.net.add_place(p)
        for i in entry.input_arcs:
            self.net.add_input(i[0], transition.name, i[2])
        for o in entry.output_arcs:
            self.net.add_output(o[0], transition.name, o[2])

        call_args = function_in(transition.name)
        call_outVars = function_out(transition.name)
        signature_args = function_in(entry.signature)
        outExprs = function_out(entry.signature)

        if len(signature_args) != len(call_args):
            raise SyntaxError('Wrong function call. Used: ' + transition.name + '. Expected: ' + entry.signature)

        for i in range(0, len(outExprs)):
            for k in range(0, len(signature_args)):
                outExprs[i] = outExprs[i].replace(signature_args[k], call_args[k])

        for (place, annotation) in transition.output():
            if type(annotation) is Variable and annotation.name in call_outVars:
                self.net.remove_output(place.name, transition.name)
                expr_instance = outExprs[call_outVars.index(annotation.name)]
                if FLUSH in expr_instance:
                    self.net.add_output(place.name, transition.name, Flush(expr_instance[len(FLUSH)+1:-1]))
                else:
                    self.net.add_output(place.name, transition.name, Expression(expr_instance))
            elif type(annotation) is Variable or type(annotation) is MultiArc:
                replaced = False
                for var in annotation.vars():
                    if var in signature_args:
                        annotation = annotation.replace(Variable(var), Variable(call_args[signature_args.index(var)]))
                        replaced = True
                    if var in call_outVars:
                        annotation = annotation.replace(Variable(var), Expression(outExprs[call_outVars.index(var)]))
                        replaced = True
                if replaced:
                    self.net.remove_output(place.name, transition.name)
                    self.net.add_output(place.name, transition.name, annotation)
            elif type(annotation) is Expression:
                expr = str(annotation)
                replaced = False
                for var in annotation.vars():
                    if var in signature_args:
                        replaced = True
                        expr = expr.replace(var, call_args[signature_args.index(var)])
                    if var in call_outVars:
                        replaced = True
                        expr = expr.replace(var, outExprs[call_outVars.index(var)])
                if replaced:
                    self.net.remove_output(place.name, transition.name)
                    self.net.add_output(place.name, transition.name, Expression(expr))
            elif type(annotation) is Flush:
                expr = str(annotation)[:-1]
                if expr.startswith('(') and expr.endswith(')'):
                    epxr = expr[1:-1]
                replaced = False
                for var in annotation.vars():
                    if var in signature_args:
                        replaced = True
                        expr = expr.replace(var, call_args[signature_args.index(var)])
                    if var in call_outVars:
                        replaced = True
                        expr = expr.replace(var, outExprs[call_outVars.index(var)])
                if replaced:
                    self.net.remove_output(place.name, transition.name)
                    self.net.add_output(place.name, transition.name, Flush(expr))

    def load_pt_from_pnml(self, pnml):
        """Load P/T elements from the `pnml` file path"""
        pnml = minidom.parse(pnml)
        for place in pnml.getElementsByTagName('place'):
            place_name = place.attributes['id'].value
            tokens = 0
            marking = place.getElementsByTagName('initialMarking')
            if len(marking)>0:
                tokens = int(marking[0].getElementsByTagName('text')[0].firstChild.nodeValue)
            self.add_place(place_name, tokens)
        for transition in pnml.getElementsByTagName('transition'):
            transition_name = transition.attributes['id'].value
            self.add_transition(transition_name)
        for arc in pnml.getElementsByTagName('arc'):
            src = arc.attributes['source'].value
            trgt = arc.attributes['target'].value
            arc_weight = arc.getElementsByTagName('inscription')
            weight = 1
            if len(arc_weight)>0:
                weight = int(arc_weight[0].getElementsByTagName('text')[0].firstChild.nodeValue)
            if T(trgt) in self.t.tokens:
                arc_type = arc.getElementsByTagName('type')
                if len(arc_type)>0 and arc_type[0].attributes['value'].value == 'inhibitor':
                    self.add_inhibitor_arc(trgt, src, weight)
                else:
                    self.add_input_arc(trgt, src, weight)
            else:
                self.add_output_arc(src, trgt, weight)

    def draw(self, dot_file=None, render=False, export_format='pdf'):
        """Export an image of the net rendered by using Graphviz"""
        dot = Digraph(comment=self.net.name,  format=export_format)
        dot.attr(rankdir='LR')
        dot.attr('node', shape='ellipse')
        for p in self.net.place():
            dot.node(p.name, str(p.tokens), xlabel=p.name)
        dot.attr('node', shape='rect')
        for t in self.net.transition():
            t_name = t.name.replace(':', '.')
            dot.node(t_name, str(t.guard), xlabel=t.name)
            for (place, annotation) in t.input():
                dot.edge(place.name, t_name, label=str(annotation))
            for (place, annotation) in t.output():
                dot.edge(t_name, place.name, label=str(annotation))
        if dot_file is None:
            print(dot.source)
        else:
            dot.render(dot_file, view=render)

    def draw_pt(self, dot_file=None, render=False, export_format='pdf'):
        """Draw the emulated net"""
        dot = Digraph(comment='Encoded P/T net', format=export_format)
        dot.attr(rankdir='LR')
        dot.attr('node', shape='circle')
        for p in self.p.tokens:
            p_name = p.replace(':', '.')
            dot.node(p_name, str(self.m.tokens(p)), xlabel=p)
        dot.attr('node', shape='rect')
        for t in self.t.tokens:
            t_name = t.replace(':', '.')
            dot.node(t_name, t)
        for (t,p) in set(list(self.i.tokens)):
            t_name = t.replace(':', '.')
            p_name = p.replace(':', '.')
            dot.edge(p_name, t_name, label=str(self.i.tokens((t,p))))
        for (t,p) in set(list(self.o.tokens)):
            t_name = t.replace(':', '.')
            p_name = p.replace(':', '.')
            dot.edge(t_name, p_name, label=str(self.o.tokens((t,p))))
        for (t,p) in set(list(self.h.tokens)):
            t_name = t.replace(':', '.')
            p_name = p.replace(':', '.')
            dot.edge(p_name, t_name, label=str(self.h.tokens((t,p))), arrowhead='odot')
        if dot_file is None:
            print(dot.source)
        else:
            dot.render(dot_file, view=render)

    def dump(self, pnml_file=None):
        """Generate a pnml dump of the emulator net"""
        if pnml_file is None:
            return dumps(self.net)
        else:
            f = open(pnml_file, 'w')
            f.write(dumps(self.net))
            f.close()

    def dump_pt(self, pnml_file=None):
        """Generate a pnml dump of the emulated net"""
        pnml = ET.Element('pnml')
        net = ET.SubElement(pnml, 'net')
        net.set('id', self.net.name)
        net.set('type', 'P/T net')
        for p in self.p.tokens:
            place = ET.SubElement(net, 'place')
            place.set('id', p.name)
            self.text_element(place, p.name)
            marking = ET.SubElement(place, 'initialMarking')
            self.text_element(marking, str(self.m.tokens(p)))
        for t in self.t.tokens:
            transition = ET.SubElement(net, 'transition')
            transition.set('id', t.name)
            self.text_element(transition, t.name)
        for (t,p) in set(list(self.i.tokens)):
            arc = ET.SubElement(net, 'arc')
            arc.set('id', p.name + ' to ' + t.name)
            arc.set('source', p.name)
            arc.set('target', t.name)
            inscription = ET.SubElement(arc, 'inscription')
            self.text_element(inscription, str(self.i.tokens((t,p))))
            type = ET.SubElement(arc, 'type')
            type.set('value', 'normal')
        for (t,p) in set(list(self.o.tokens)):
            arc = ET.SubElement(net, 'arc')
            arc.set('id', t.name + ' to ' + p.name)
            arc.set('source', t.name)
            arc.set('target', p.name)
            inscription = ET.SubElement(arc, 'inscription')
            self.text_element(inscription, str(self.o.tokens((t,p))))
            type = ET.SubElement(arc, 'type')
            type.set('value', 'normal')
        for (t,p) in set(list(self.h.tokens)):
            arc = ET.SubElement(net, 'arc')
            arc.set('id', p.name + ' to ' + t.name)
            arc.set('source', p.name)
            arc.set('target', t.name)
            inscription = ET.SubElement(arc, 'inscription')
            self.text_element(inscription, str(self.h.tokens((t,p))))
            type = ET.SubElement(arc, 'type')
            type.set('value', 'inhibitor')
        if pnml_file is None:
            print(ET.tostring(pnml))
        else:
            tree = ET.ElementTree(pnml)
            tree.write(pnml_file, xml_declaration=True, encoding='utf-8', method='xml')

    def text_element(self, el, text):
        txt_el = ET.SubElement(el, 'text')
        txt_el.text = text
        return txt_el

    def __del__(self):
        self.p = None
        self.t = None
        self.m = None
        self.i = None
        self.o = None
        self.h = None
        self.net = None

# class P:
#     """Instances of this class represent PT places"""
#
#     def __init__(self, pl_name):
#         self.name = pl_name
#
#     @property
#     def name(self):
#         return self.__name
#
#     @name.setter
#     def name(self, pl_name):
#         self.__name = pl_name
#
#     def __eq__(self, other):
#         return self.__repr__() == other.__repr__()
#
#     def __ne__(self, other):
#         return not self.__eq__(other)
#
#     def __hash__(self):
#         return hash(self.__repr__())
#
#     def __str__(self):
#         return 'P(' + self.name + ')'
#
#     def __repr__(self):
#         return 'P(' + self.name + ')'
#
# class T:
#     """Instances of this class represent PT transitions"""
#
#     def __init__(self, tr_name):
#         self.name = tr_name
#
#     @property
#     def name(self):
#         return self.__name
#
#     @name.setter
#     def name(self, tr_name):
#         self.__name = tr_name
#
#     def __eq__(self, other):
#         return self.__repr__() == other.__repr__()
#
#     def __ne__(self, other):
#         return not self.__eq__(other)
#
#     def __hash__(self):
#         return hash(self.__repr__())
#
#     def __str__(self):
#         return 'T(' + self.name + ')'
#
#     def __repr__(self):
#         return 'T(' + self.name + ')'


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


# Utility functions used to implement the unfolding

def function_name(call_str):
    """Return the lib function name, given the user defined transition name.
    e.g., function_name('lib::getMarking(p) := n') = 'lib::getMarking' """
    return call_str[:call_str.find('(')]

def function_in(strFunct):
    """Return the list of input variables, given a function signature.
    e.g., function_in('lib::name(a, b) := n') = ['a', 'b'] """
    result = [v.strip() for v in strFunct[strFunct.find('(')+1:strFunct.find(')')].split(ARG_SEPARATOR)]
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
