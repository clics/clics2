# coding: utf8
from collections import defaultdict

import igraph

__all__ = ['full_colexification', 'networkx2igraph']


def networkx2igraph(graph):
    """Helper function converts networkx graph to igraph graph object."""
    newgraph = igraph.Graph(directed=graph.is_directed())
    nodes = {}
    for i, (node, data) in enumerate(graph.nodes(data=True)):
        data = {a: b for a, b in data.items()}
        newgraph.add_vertex(
            i, Name=node, **{a: b for a, b in data.items() if a not in ['Name', 'name']})
        nodes[node] = i
    for node1, node2, data in graph.edges(data=True):
        newgraph.add_edge(nodes[node1], nodes[node2], **{a: b for a, b in data.items()})
    return newgraph


def full_colexification(forms):
    """
    Calculate all colexifications inside a wordlist.

    :param forms: The forms of a wordlist.

    :return: colexifictions, a dictionary taking the entries as keys and tuples
        consisting of a concept and its index as values
    :rtype: dict

    Note
    ----
    Colexifications are identified using a hash (Python dictionary) and a
    linear iteration through the graph. As a result, this approach is very
    fast, yet the results are potentially a bit counter-intuitive, as they are
    presented as a dictionary containing word values as keys. To get all
    colexifications in sets, however, you can just take the values of the
    dictionary.
    """
    cols = defaultdict(list)
    for form in forms:
        if form.clics_form and form.concepticon_id:
            cols[form.clics_form].append(form)
    return cols
