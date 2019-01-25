from snakes.nets import *
import snakes.plugins
from snakes.pnml import dumps, loads
from xml.dom import minidom
import xml.etree.ElementTree as ET
from graphviz import Digraph
from enum import Enum

from .functions import keys, values, intersection
from .base import Emulator
from .primitives import *

class MAPE(Enum):
    NONE = 0
    M = 1 # MONITOR
    A = 2 # ANALYZE
    P = 3 # PLAN
    E = 4 # EXECUTE
    K = 5 # KNOWLEDGE

class AdaptiveNetBuilder:

    def __init__(self, emulator=Emulator()):
        self.net = emulator.get_net().copy()
        self.primitives = dict(READ_LIB, **WRITE_LIB)
        self.observe = {}
        self.loop_counter = 1

    def add_loop(self, loop=None, initial_places=[], observable_events=[]):
        for p in loop.get_net().place():
            self.net.add_place(p.copy())
        for t in loop.get_net().transition():
            self.net.add_transition(Transition(t.name, t.guard))
            for i in t.input():
                self.net.add_input(i[0].name, t.name, i[1])
            for o in t.output():
                self.net.add_output(o[0].name, t.name, o[1])
        if len(observable_events) > 0:
            events = tuple(observable_events)
            if self.observe.get(events) is None:
                self.net.place('observable').add(MultiSet(observable_events))
                self.observe.update({events : self.loop_counter})
                self.net.add_place(Place('observable' + str(self.loop_counter), observable_events))
                self.create_moveTransition(self.loop_counter)
                self.loop_counter += 1
            counter = self.observe.get(events)
            for p in initial_places:
                self.net.add_output(p, 'move' + str(counter), Variable('t'))
        return self

    def create_moveTransition(self, counter):
        move_name = 'move' + str(counter)
        observable_name = 'observable' + str(counter)
        self.net.add_transition(Transition(move_name, Expression('value(i, t) <= MultiSet(m) and (len(value(h, t))==0 or value(h, t) > projection(m, value(h, t))) and e(t)>0')))
        self.net.add_input('O', move_name, Flush('o'))
        self.net.add_output('O', move_name, Flush('o'))
        self.net.add_input('I', move_name, Flush('i'))
        self.net.add_output('I', move_name, Flush('i'))
        self.net.add_input('H', move_name, Flush('h'))
        self.net.add_output('H', move_name, Flush('h'))
        self.net.add_input('T', move_name, Variable('t'))
        self.net.add_output('T', move_name, Variable('t'))
        self.net.add_input('M', move_name, Flush('m'))
        self.net.add_output('M', move_name, Flush('MultiSet(m) - value(i, t) + value(o, t)'))
        self.net.add_input(observable_name, move_name, Flush('e'))
        self.net.add_output(observable_name, move_name, Flush('e'))

    def add_functions(functions=None):
        if functions is not None:
            self.net.globals.declare("from " + functions + " import *")

    def build(self):
        self.unfold_net()
        return self.net

    def unfold_net(self):
        """Unfold all the lib:: transitions"""
        for t in self.net.transition():
            if t.name.startswith(LIB_PREFIX) and self.primitives.get(function_name(t.name)) is not None:
                self.unfold(t, self.primitives.get(function_name(t.name)))

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


class FeedbackLoop:

    def __init__(self, name='loop'):
        self.net = PetriNet(name)
        self.zones = { }

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
