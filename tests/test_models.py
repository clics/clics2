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
    graphdir = str(tmpdir)
    n = Network('g', 't', 'e', graphdir)
    p = n.save(_make_graph())
    assert p.name == 'g-t-e.gml'
    assert p.exists()
    assert n.components() == [{'n1', 'n2'}]
    assert n.communities()['x'] == ['n1']
