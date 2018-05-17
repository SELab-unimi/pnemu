from snakes.nets import *
import snakes.plugins
from snakes.pnml import dumps, loads
from xml.dom import minidom
import xml.etree.ElementTree as ET
from graphviz import Digraph

from .functions import keys, values, intersection

LIB_PREFIX = 'lib::'
FLUSH = 'flush'
ASSIGNMENT = ':='
ARG_SEPARATOR = ','
RESULT_SEPARATOR = ';'

class Emulator:

    def __init__(self, pt_net=None, functions=None):
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

        # import functions attached to arcs/transitions
        self.net.globals.declare('from pnemu.functions import *')
        #self.net.globals.declare('import math')
        # Extension point: import a collection of custom python-functions to be used in user-defined core lib functions
        if functions is not None:
            self.net.globals.declare("from " + functions + " import *")

        self.core_lib = CORE_LIB

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

    def add_place(self, place, tokens=None):
        p = Place(place)
        if tokens is not None:
            p.add(tokens)
        self.net.add_place(p)

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
            p_name = p.name.replace(':', '.')
            dot.node(p_name, str(self.m.tokens(p)), xlabel=p.name)
        dot.attr('node', shape='rect')
        for t in self.t.tokens:
            t_name = t.name.replace(':', '.')
            dot.node(t_name, t.name)
        for (t,p) in set(list(self.i.tokens)):
            t_name = t.name.replace(':', '.')
            p_name = p.name.replace(':', '.')
            dot.edge(p_name, t_name, label=str(self.i.tokens((t,p))))
        for (t,p) in set(list(self.o.tokens)):
            t_name = t.name.replace(':', '.')
            p_name = p.name.replace(':', '.')
            dot.edge(t_name, p_name, label=str(self.o.tokens((t,p))))
        for (t,p) in set(list(self.h.tokens)):
            t_name = t.name.replace(':', '.')
            p_name = p.name.replace(':', '.')
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


# CORE LIB (read) to implement Sensors in Monitor components
# `lib::getTokens(p) := n` given a P as input var `p`, it returns a natural number (>= 0) into var `n`
# `lib::getMarking() := m` returns a multiset of P into var `m` (multiplicity represents the number of tokens)
# `lib::getPlaces() := p` returns a multiset of P `p`
# `lib::getTransitions() := t` returns a multiset of T in var `t`
# `lib::exists(e) := v`: returns True in var `v` iff the element (either a P or a T) in var `e` exists
# `lib::pre(e) := r` given an element (either a P or a T) in var `e`, it returns a multiset of P/T belonging to the preset of `e` (multiplicity represents the arc weight)
# `lib::post(e) := r` given an element (either a P or a T) in var `e`, it returns a multiset of P/T belonging to the postset of `e` (multiplicity represents the arc weight)
# `lib::inh(e) := r`: given an element (either a P or a T) in var `e`, it returns a multiset of P/T s.t. the element `e` inhibits/is-inhibitor of (multiplicity represents the arc weight)
# `lib::iMult(p,t) := n`: givent a P `p` and a T `t`, it returns the multiplicity of the input arc (p,t)
# `lib::hMult(p,t) := n`: givent a P `p` and a T `t`, it returns the multiplicity of the inhibitor arc (p,t)
# `lib::oMult(t,p) := n`: givent a T `t` and a P `p`, it returns the multiplicity of the output arc (t,p)

# ASSUMPTION
# the user uses lowercase letters for variables (e.g., p, t, h)
# uppercase letters (e.g., M, I, H, ...) and lowercase letters followed by `_` (e.g., p_, i_, h_) are reserved names

CORE_LIB = { }
signature = LIB_PREFIX + "getTokens(p_) := m(p_)"
entry = LibEntry(
    signature,
    [Place('M')],
    [('M', signature, Flush('m'))],
    [('M', signature, Flush('m'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getMarking() := flush(m)"
entry = LibEntry(
    signature,
    [Place('M')],
    [('M', signature, Flush('m'))],
    [('M', signature, Flush('m'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getPlaces() := flush(p)"
entry = LibEntry(
    signature,
    [Place('P')],
    [('P', signature, Flush('p'))],
    [('P', signature, Flush('p'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "getTransitions() := flush(t)"
entry = LibEntry(
    signature,
    [Place('T')],
    [('T', signature, Flush('t'))],
    [('T', signature, Flush('t'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "exists(e_) := p(e_)>0 or t(e_)>0"
entry = LibEntry(
    signature,
    [Place('P'), Place('T')],
    [('P', signature, Flush('p')), ('T', signature, Flush('t'))],
    [('P', signature, Flush('p')), ('T', signature, Flush('t'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "pre(e_) := flush(values(i, e_) + keys(o, e_))"
entry = LibEntry(
    signature,
    [Place('I'), Place('O')],
    [('I', signature, Flush('i')), ('o', signature, Flush('O'))],
    [('I', signature, Flush('i')), ('o', signature, Flush('O'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "post(e_) := flush(values(o, e_) + keys(i, e_))"
entry = LibEntry(
    signature,
    [Place('I'), Place('O')],
    [('I', signature, Flush('i')), ('o', signature, Flush('O'))],
    [('I', signature, Flush('i')), ('o', signature, Flush('O'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "inh(e_) := flush(values(h, e_) + keys(h, e_))"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('h'))],
    [('H', signature, Flush('h'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "hMult(p_,t_) := H((t_, p_))"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('h'))],
    [('H', signature, Flush('h'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "iMult(p_,t_) := i((t_, p_))"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Flush('i'))],
    [('I', signature, Flush('i'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "oMult(t_,p_) := o((t_, p_))"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Flush('o'))],
    [('O', signature, Flush('o'))])
CORE_LIB.update({function_name(signature) : entry})


# CORE LIB (write) to implement Actuators in Execute components
# `lib::addPlace(p)` it adds the P contained in var `p` into the reifiction place `P`
# `lib::addTransition(t)` it adds the T contained in var `t` into the reifiction place `T`
# `lib::setTokens(p, n)` given a P (`p` var) and a number (`n` var), it mofifies the marking of the reification place `M` by setting the number of tokens in `p` to `n`
# `lib::addInputArc(p, t, n)` given a P (`p` var), a T (`t` var) and a number (`n` var), it adds an input arc (p, t) with multiplicity n into the place `I` of the reification
# `lib::addOutputArc(p, t, n)` given a P (`p` var), a T (`t` var) and a number (`n` var), it adds an output arc (p, t) with multiplicity n into the place `O` of the reification
# `lib::addInhibitorArc(p, t, n)` given a P (`p` var), a T (`t` var) and a number (`n` var), it adds an inhibitor arc (p, t) with multiplicity n into the place `H` of the reification
# `lib::removePlace(p)` given a P (`p` var), it removes the place p from `P` of the reification (it also removes connected arcs)
# `lib::removeTransition(t)` given a T (`t` var), it removes the transition t from `T` of the reification (it also removes connected arcs)
# `lib::removeInputArc(p, t, n)`given a P (`p` var), a T (`t` var) and a number (`n` var), it reduces the multiplicity of the input arc (p, t) by n, in `I` of the reification
# `lib::removeOutputArc(p, t, n)`given a P (`p` var), a T (`t` var) and a number (`n` var), it reduces the multiplicity of the output arc (p, t) by n, in `O` of the reification
# `lib::removeInhibitorArc(p, t, n)`given a P (`p` var), a T (`t` var) and a number (`n` var), it reduces the multiplicity of the inhibitor arc (p, t) by n, in `H` of the reification

# ASSUMPTION
# the user uses lowercase letters for variables (e.g., p, t, h)
# uppercase letters (e.g., M, I, H, ...) and lowercase letters followed by `_` (e.g., p_, i_, h_) are reserved names

signature = LIB_PREFIX + "addPlace(p_)"
entry = LibEntry(
    signature,
    [Place('P')],
    [],
    [('P', signature, Variable('p_'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addTransition(t_)"
entry = LibEntry(
    signature,
    [Place('T')],
    [],
    [('T', signature, Variable('t_'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "setTokens(p_, n_)"
entry = LibEntry(
    signature,
    [Place('M')],
    [('M', signature, Flush('m'))],
    [('M', signature, Flush('setMultiplicity(m, p_, n_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addInputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Flush('i'))],
    [('I', signature, Flush('i + MultiSet([(t_, p_)] * n_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addOutputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Flush('o'))],
    [('O', signature, Flush('o + MultiSet([(t_, p_)] * n_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "addInhibitorArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('h'))],
    [('H', signature, Flush('h + MultiSet([(t_, p_)] * n_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removePlace(p_)"
entry = LibEntry(
    signature,
    [Place('P'), Place('I'), Place('O'), Place('H'), Place('M')],
    [('P', signature, Flush('p')), ('I', signature, Flush('i')), ('O', signature, Flush('O')), ('H', signature, Flush('h')), ('M', signature, Flush('m'))],
    [('P', signature, Flush('p - MultiSet([p_])')), ('I', signature, Flush('i - filterByValue(i, p_)')), ('O', signature, Flush('o - filterByValue(o, p_)')), ('H', signature, Flush('h - filterByValue(h, p_)')), ('M', signature, Flush('m - MultiSet([p_] * M(p_))'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeTransition(t_)"
entry = LibEntry(
    signature,
    [Place('T'), Place('I'), Place('O'), Place('H')],
    [('T', signature, Flush('T')), ('I', signature, Flush('i')), ('O', signature, Flush('o')), ('H', signature, Flush('h'))],
    [('T', signature, Flush('T - MultiSet([t_])')), ('I', signature, Flush('i - filterByKey(i, t_)')), ('O', signature, Flush('o - filterByKey(o, t_)')), ('H', signature, Flush('h - filterByKey(h, t_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeInputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('I')],
    [('I', signature, Flush('i'))],
    [('I', signature, Flush('i - MultiSet([(t_, p_)] * n_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeOutputArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('O')],
    [('O', signature, Flush('o'))],
    [('O', signature, Flush('o - MultiSet([(t_, p_)] * n_)'))])
CORE_LIB.update({function_name(signature) : entry})
signature = LIB_PREFIX + "removeInhibitorArc(p_, t_, n_)"
entry = LibEntry(
    signature,
    [Place('H')],
    [('H', signature, Flush('h'))],
    [('H', signature, Flush('h - MultiSet([(t_, p_)] * n_)'))])
CORE_LIB.update({function_name(signature) : entry})
