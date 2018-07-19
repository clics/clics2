import os

import networkx

from pyclics.models import *


def test_Variety():
    v = Variety('id', 'source', 'name', 'gc', 'f', 'ma', 1.2, 2.3)
    assert v.gid == 'source-id'
    assert v.as_geojson()['geometry'] is not None

    v = Variety('id', 'source', 'name', 'gc', 'f', 'ma', None, None)
    assert v.as_geojson()['geometry'] is None


def test_Concept():
    c = Concept('id', 'gloss', 'oc', 'sc')
    assert isinstance(c.as_node_attrs(), dict)


def _make_graph():
    g = networkx.Graph()
    g.add_node('n1', infomap='x')
    g.add_node('n2')
    g.add_edge('n1', 'n2')
    return g


def test_Network(tmpdir):
    graphdir = str(tmpdir.join('graphs'))
    n = Network('g', 't', 'e', graphdir=graphdir)
    assert n.fname('svg').name == 'g-t-e.svg'

    p = n.save(_make_graph())
    assert p.name == 'g-t-e.gml'
    assert p.exists()

    g1 = n.load()
    os.remove(os.path.join(graphdir, 'g-t-e.bin'))
    g2 = n.load()
    assert g1.nodes() == g2.nodes()
    n.G = None
    assert n.components() == [{'n1', 'n2'}]
    n.G = None
    assert n.communities()['x'] == ['n1']
