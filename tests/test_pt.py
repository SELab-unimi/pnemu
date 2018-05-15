from .context import PT
from snakes.nets import Place

import os
import unittest

TEST_PNML_1 = os.path.join(os.path.dirname(__file__), 'resources/test.pnml')
TEST_PNML_2 = os.path.join(os.path.dirname(__file__), 'resources/test2.pnml')
TEST_DOT = os.path.join(os.path.dirname(__file__), 'resources/example.dot')

class PTNetTestSuite(unittest.TestCase):

    def setup_method(self, method):
        self.pt = PT('Simple P/T net')

    def teardown_method(self, method):
        self.pt = None

    def test_PT_place(self):
        self.pt.add_place('p0')
        self.assertIsNotNone(self.pt.get_place('p0'))
        assert self.pt.get_place('p0').name == 'p0'
        self.pt.add_place('p1', 5)
        assert self.pt.get_tokens('p0') == 0
        assert self.pt.get_tokens('p1') == 5
        self.pt.set_tokens('p1', 0)
        assert self.pt.get_tokens('p0') == 0

    def test_PT_arc(self):
        # input arcs
        self.pt.add_place('p0')
        self.pt.add_transition('t0')
        assert len(self.pt.input_arcs('t0')) == 0
        self.pt.add_input_arc('p0', 't0')
        assert len(self.pt.input_arcs('t0')) == 1
        self.pt.add_place('p1')
        self.pt.add_input_arc('p1', 't0', 2)
        assert len(self.pt.input_arcs('t0')) == 2
        # output arcs
        assert len(self.pt.output_arcs('t0')) == 0
        self.pt.add_output_arc('t0', 'p1')
        assert len(self.pt.output_arcs('t0')) == 1
        self.pt.add_output_arc('t0', 'p0')
        assert len(self.pt.output_arcs('t0')) == 2
        # inhibitor arcs
        self.pt.add_place('p2')
        self.pt.add_place('p3')
        assert len(self.pt.inhibitor_arcs('t0')) == 0
        self.pt.add_inhibitor_arc('p2', 't0', 2)
        assert len(self.pt.inhibitor_arcs('t0')) == 1
        self.pt.add_inhibitor_arc('p3', 't0')
        assert len(self.pt.inhibitor_arcs('t0')) == 2

    def test_PT_enab(self):
        # without inhibitor arcs
        self.pt.add_place('p0', 3)
        self.pt.add_transition('t0')
        self.pt.add_input_arc('p0', 't0', 2)
        assert self.pt.enabled('t0')
        self.pt.add_place('p1', 1)
        self.pt.add_input_arc('p1', 't0', 3)
        assert not self.pt.enabled('t0')
        # with inhibitor arcs
        self.pt.set_tokens('p1', 3)
        assert self.pt.enabled('t0')
        self.pt.add_place('p2', 2)
        self.pt.add_inhibitor_arc('p2', 't0')
        assert not self.pt.enabled('t0')

    def test_PT_fire(self):
        self.pt.add_place('p0', 3)
        self.pt.add_place('p1')
        self.pt.add_transition('t0')
        self.pt.add_input_arc('p0', 't0', 3)
        self.pt.add_output_arc('t0', 'p1', 2)
        assert self.pt.enabled('t0')
        assert self.pt.get_tokens('p0') == 3
        assert self.pt.get_tokens('p1') == 0
        self.pt.fire('t0')
        assert self.pt.get_tokens('p0') == 0
        assert self.pt.get_tokens('p1') == 2
        assert not self.pt.enabled('t0')

    def test_PT_import(self):
        # example taken from https://mcc.lip6.fr/models.php (ClientsAndServers model)
        pt_from_pnml = PT('load_test', TEST_PNML_1)
        assert len(pt_from_pnml.get_places()) == 25
        assert len(pt_from_pnml.get_transitions()) == 18
        assert len(pt_from_pnml.get_arcs()) == 54
        # small example with inhibitor arcs and weights
        pt_from_pnml2 = PT('load_test', TEST_PNML_2)
        self.assertIsNotNone(pt_from_pnml2.get_place('P0'))
        assert pt_from_pnml2.get_tokens('P0') == 3
        assert len(pt_from_pnml2.input_arcs('T1')) == 1
        assert list(pt_from_pnml2.input_arcs('T1'))[0].weight == 3
        assert len(pt_from_pnml2.inhibitor_arcs('T0')) == 1
        assert list(pt_from_pnml2.inhibitor_arcs('T0'))[0].weight == 2
        assert len(pt_from_pnml2.output_arcs('T0')) == 0
        assert len(pt_from_pnml2.output_arcs('T1')) == 0
        assert not pt_from_pnml2.enabled('T0')
        assert pt_from_pnml2.enabled('T1')
        pt_from_pnml2.fire('T1')
        assert pt_from_pnml2.get_tokens('P0') == 0
        assert pt_from_pnml2.enabled('T0')

    def test_PT_dot_export(self):
        try:
            os.remove(TEST_DOT)
        except OSError:
            pass
        pt = PT('load_test', TEST_PNML_1)
        pt.export_dot(TEST_DOT)
        assert os.path.isfile(TEST_DOT) and os.path.getsize(TEST_DOT)>0
        try:
            os.remove(TEST_DOT)
            os.remove(TEST_DOT + '.pdf')
        except OSError:
            pass

if __name__ == '__main__':
    unittest.main()
