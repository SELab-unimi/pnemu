from snakes.nets import *
from graphviz import Digraph
from xml.dom import minidom
import xml.etree.ElementTree as ET

class Emulator:

    def __init__(self, pt_net=None, concur=True, neco_analysis=False):
        self.net = PetriNet('emulator')

        # basic components
        self.m = Place('M')
        self.o = Place('O')
        self.i = Place('I')
        self.h = Place('H')
        self.t = Place('T')
        self.p = Place('P')
        self.e = Place('observable')
        self.net.add_place(self.m)
        self.net.add_place(self.o)
        self.net.add_place(self.i)
        self.net.add_place(self.h)
        self.net.add_place(self.t)
        self.net.add_place(self.p)
        self.net.add_place(self.e)

        # `move` transition for P/T emulation
        #self.net.add_transition(Transition('move', Expression('value(i, t) <= MultiSet(m) and (len(value(h, t))==0 or value(h, t) > projection(m, value(h, t)) and e(t)==0')))
        self.net.add_transition(Transition('move', Expression('value(i, t) <= MultiSet(m) and (len(value(h, t))==0 or len(projection(m, value(h, t)))==0) and e(t)==0')))

        # arcs connecting basic components and the `move` transition
        # Test annotatation not supported by neco-compiler
        #self.net.add_input('O', 'move', Test(Flush('o')))
        #self.net.add_input('I', 'move', Test(Flush('i')))
        #self.net.add_input('H', 'move', Test(Flush('h')))
        #self.net.add_input('T', 'move', Test(Variable('t')))
        self.net.add_input('O', 'move', Flush('o'))
        self.net.add_output('O', 'move', Flush('o'))
        self.net.add_input('I', 'move', Flush('i'))
        self.net.add_output('I', 'move', Flush('i'))
        self.net.add_input('H', 'move', Flush('h'))
        self.net.add_output('H', 'move', Flush('h'))
        self.net.add_input('T', 'move', Variable('t'))
        self.net.add_output('T', 'move', Variable('t'))
        self.net.add_input('M', 'move', Flush('m'))
        self.net.add_output('M', 'move', Flush('MultiSet(m) - value(i, t) + value(o, t)'))
        self.net.add_input('observable', 'move', Flush('e'))
        self.net.add_output('observable', 'move', Flush('e'))

        if not concur:
            self.net.add_place(Place('firable', True))
            self.net.add_input('firable', 'move', Variable('b'))

        # import functions attached to arcs/transitions
        #self.net.globals.declare('import math')
        if(not neco_analysis):
            self.net.globals.declare('from pnemu.functions import *')

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

    def modes(self, tr='move'):
        return self.net.transition(tr).modes()

    def fire(self, mode, tr='move'):
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

class PT:

    def __init__(self, net_name, pnml=None):
        self.name = net_name
        self.places = {}
        self.transitions = {}
        self.marking = {}
        self.i = {}
        self.o = {}
        self.h = {}
        if pnml is not None:
            self.load_pnml(pnml)

    def add_transition(self, transition_name):
        """Add a transition named `transition_name`"""
        self.transitions.update({transition_name : Transition(transition_name)})

    def add_input_arc(self, place_name, transition_name, weight=1):
        """Add an input arc from the place `place_name` to the transition `transition_name`"""
        if place_name in self.places and transition_name in self.transitions:
            self.add_arc(place_name, transition_name, transition_name, weight, self.i)

    def add_output_arc(self, transition_name, place_name, weight=1):
        """Add an output arc from the transition `transition_name` to the place `place_name`"""
        if place_name in self.places and transition_name in self.transitions:
            self.add_arc(transition_name, place_name, transition_name, weight, self.o)

    def add_inhibitor_arc(self, place_name, transition_name, weight=1):
        """Add an inhibitor arc from the place `place_name` to the transition `transition_name`"""
        if place_name in self.places and transition_name in self.transitions:
            self.add_arc(place_name, transition_name, transition_name, weight, self.h)

    def add_arc(self, src, trgt, transition_name, weight, arc_map):
        arcs = []
        if transition_name in arc_map:
            arcs = arc_map.get(transition_name)
        arcs += [Arc(src, trgt, weight)]
        arc_map.update({transition_name : arcs})

    def input_arcs(self, node_name):
        """Returns the input arcs of the transition named `node_name`"""
        if node_name in self.transitions and node_name in self.i:
            return set(self.i.get(node_name))
        return set()

    def output_arcs(self, node_name):
        """Returns the output arcs of the node named `node_name`"""
        if node_name in self.transitions and node_name in self.o:
            return set(self.o.get(node_name))
        return set()

    def inhibitor_arcs(self, node_name):
        """Returns the inhibitor arcs of the node named `node_name`"""
        if node_name in self.transitions and node_name in self.h:
            return set(self.h.get(node_name))
        return set()

    def add_place(self, place_name, tokens=0):
        """Add a place with specified `place_name` and `tokens` (0 by default)"""
        self.places.update({place_name : Place(place_name)})
        self.set_tokens(place_name, tokens)

    def set_tokens(self, place_name, tokens):
        """Set #`tokens` tokens into the place named `place_name`"""
        if place_name in self.places:
            if tokens>0:
                self.marking.update({place_name : tokens})
            if tokens==0 and place_name in self.marking:
                del self.marking[place_name]

    def get_tokens(self, place_name):
        """Return the number of tokens in place named `place_name`"""
        if place_name in self.places and place_name in self.marking:
            return self.marking.get(place_name)
        return 0

    def get_place(self, place_name):
        """Return a specific place named `place_name`"""
        if place_name in self.places:
            return self.places.get(place_name)
        return None

    def enabled(self, transition_name):
        """Return True if the `transition_name` transition is enabled in the current marking"""
        if transition_name not in self.transitions:
            return False
        for input_arc in self.input_arcs(transition_name):
            if self.get_tokens(input_arc.src) < input_arc.weight:
                    return False
        for inhibitor_arc in self.inhibitor_arcs(transition_name):
            if self.get_tokens(inhibitor_arc.src) >= inhibitor_arc.weight:
                    return False
        return True

    def fire(self, transition_name):
        """Fire the transition `transition_name`, if enabled"""
        if self.enabled(transition_name):
            for i in self.input_arcs(transition_name):
                self.set_tokens(i.src, self.get_tokens(i.src)-i.weight)
            for o in self.output_arcs(transition_name):
                self.set_tokens(o.dst, self.get_tokens(o.dst)+o.weight)

    def get_marking(self):
        return self.marking

    def load_pnml(self, pnml):
        """Load PT elements from the `pnml` file path"""
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
            if trgt in self.transitions:
                arc_type = arc.getElementsByTagName('type')
                if len(arc_type)>0 and arc_type[0].attributes['value'].value == 'inhibitor':
                    self.add_inhibitor_arc(src, trgt, weight)
                else:
                    self.add_input_arc(src, trgt, weight)
            else:
                self.add_output_arc(src, trgt, weight)

    def export_dot(self, dot_file=None):
        dot = Digraph(comment=self.name)
        dot.attr('node', shape='circle')
        for p in self.places:
            dot.node(p, str(self.get_tokens(p)), xlabel=p)
        dot.attr('node', shape='rect')
        for t in self.transitions:
            dot.node(t, t)
        for t in self.i:
            for i in self.i.get(t):
                dot.edge(i.src, i.dst, label=str(i.weight))
        for t in self.o:
            for o in self.o.get(t):
                dot.edge(o.src, o.dst, label=str(o.weight))
        for t in self.h:
            for h in self.h.get(t):
                dot.edge(h.src, h.dst, label=str(h.weight), arrowhead='odot')
        if dot_file is None:
            print(dot.source)
        else:
            dot.render(dot_file, view=False)


    def __del__(self):
        self.places.clear()
        self.transitions.clear()
        self.marking.clear()
        self.i.clear()
        self.o.clear()
        self.h.clear()

    def get_name(self):
        return self.name

    def get_places(self):
        return self.places

    def get_transitions(self):
        return self.transitions

    def get_input_arcs(self):
        return self.i

    def get_output_arcs(self):
        return self.o

    def get_inhibitor_arcs(self):
        return self.h

    def get_arcs(self):
        result = []
        for i in self.i:
            result += self.i.get(i)
        for o in self.o:
            result += self.o.get(o)
        for h in self.h:
            result += self.h.get(h)
        return result


class Arc:

    def __init__(self, src_node_name, dst_node_name, w=1):
        self.src = src_node_name
        self.dst = dst_node_name
        self.weight = w

    @property
    def src(self):
        return self.__src

    @src.setter
    def src(self, src_node_name):
        self.__src = src_node_name

    @property
    def dst(self):
        return self.__dst

    @dst.setter
    def dst(self, dst_node_name):
        self.__dst = dst_node_name

    @property
    def weight(self):
        return self.__weight

    @weight.setter
    def weight(self, w):
        if w > 0:
            self.__weight = w

    def __repr__(self):
        return 'Arc(' + self.src + ', ' + self.dst + ', ' + str(self.weight) + ')'
