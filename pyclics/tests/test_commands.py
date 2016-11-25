from pyclics.commands import get_cocitation_graph
from pyclics.utils import *

vs, igr, G = get_cocitation_graph('digraph', 0, 'families')
keep_edges = {}
for i, v in enumerate(vs):
    label = igr.vs[i]['Gloss']
    if sum(v):
        labs = [label]
        for j, c in enumerate(v):
            if c:
                labs += [igr.vs[j]['Gloss']]
                keep_edges[igr.vs[i]['Name'], igr.vs[j]['Name']] = c
        print(', '.join(labs))
remove_edges = []
for nA, nB in G.edges():
    if (nA, nB) in keep_edges:
        G.edge[nA][nB]['bibcoupling'] = keep_edges[nA, nB]
    else:
        remove_edges += [(nA, nB)]
G.remove_edges_from(remove_edges)
G2 = G.to_undirected()
save_network(clics_path('graphs', 'coupling-0-families.gml'), G2, dump=True)
