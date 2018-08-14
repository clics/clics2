# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict
from itertools import combinations, groupby
import sqlite3
from pathlib import Path
import shutil

from tqdm import tqdm
import geojson
from clldutils.clilib import command, ParserError
from clldutils.markup import Table
from clldutils import jsonlib
from pyconcepticon.api import Concepticon
from pyglottolog.api import Glottolog
from pylexibank.dataset import iter_datasets
import networkx as nx
from networkx.readwrite import json_graph
from tabulate import tabulate

from pyclics.util import full_colexification, networkx2igraph


@command('datasets')
def list_(args):
    """List datasets available for loading

    clics --lexibank-repos=PATH/TO/lexibank-data list
    """
    if args.unloaded:
        i = 0
        for i, ds in enumerate(iter_datasets()):
            print(ds.cldf_dir)
        if not i:
            print('No datasets installed')  # pragma: no cover
    else:
        table = Table(
            '#', 'Dataset', 'Glosses', 'Concepticon', 'Varieties', 'Glottocodes', 'Families')
        try:
            concept_counts = {r[0]: r[1:] for r in args.api.db.fetchall('concepts_by_dataset')}
        except sqlite3.OperationalError:  # pragma: no cover
            print('No datasets loaded yet')
            return

        varieties = args.api.db.varieties
        var_counts = {}
        for dsid, vs in groupby(varieties, lambda v: v.source):
            vs = list(vs)
            var_counts[dsid] = (
                len(vs), len(set(v.glottocode for v in vs)), len(set(v.family for v in vs)))

        for count, d in enumerate(args.api.db.datasets):
            table.append([
                count + 1,
                d.replace('lexibank-', ''),
                concept_counts[d][1],
                concept_counts[d][0],
                var_counts[d][0],
                var_counts[d][1],
                var_counts[d][2],
            ])
        table.append([
            '',
            'TOTAL',
            0,
            args.api.db.fetchone(
                """\
select
    count(distinct p.concepticon_id) from parametertable as p, formtable as f, languagetable as l
where
    f.parameter_id = p.id and f.dataset_id = p.dataset_id
    and f.language_id = l.id and f.dataset_id = l.dataset_id
    and l.glottocode is not null
    and l.family != 'Bookkeeping'
""")[0],
            len(varieties),
            len(set(v.glottocode for v in varieties)),
            len(set(v.family for v in varieties))
        ])
        print(table.render(tablefmt='simple'))


@command()
def load(args):
    """
    clics load /path/to/concepticon-data /path/to/glottolog
    """
    if len(args.args) != 2:
        raise ParserError('concepticon and glottolog repos locations must be specified!')
    concepticon = Path(args.args[0])
    if not concepticon.exists():
        raise ParserError('concepticon repository does not exist')
    glottolog = Path(args.args[1])
    if not glottolog.exists():
        raise ParserError('glottolog repository does not exist')

    args.api.db.create(exists_ok=True)
    args.log.info('loading datasets into {0}'.format(args.api.db.fname))
    in_db = args.api.db.datasets
    for ds in iter_datasets():
        if args.unloaded and ds.id in in_db:
            args.log.info('skipping {0} - already loaded'.format(ds.id))
            continue
        args.log.info('loading {0}'.format(ds.id))
        args.api.db.load(ds)
    args.log.info('loading Concepticon data')
    args.api.db.load_concepticon_data(Concepticon(str(concepticon)))
    args.log.info('loading Glottolog data')
    args.api.db.load_glottolog_data(Glottolog(str(glottolog)))
    return


@command()
def colexification(args):
    args.api._log = args.log
    threshold = args.threshold or 1
    edgefilter = args.edgefilter
    words = {}

    def clean(word):
        return ''.join([w for w in word if w not in '/,;"'])

    varieties = args.api.db.varieties
    lgeo = geojson.FeatureCollection([v.as_geojson() for v in varieties])
    args.api.json_dump(lgeo, 'app', 'source', 'langsGeo.json')

    app_source = args.api.existing_dir('app', 'source')
    for p in Path(__file__).parent.joinpath('app').iterdir():
        target_dir = app_source.parent if p.suffix == '.html' else app_source
        shutil.copy(str(p), str(target_dir / p.name))

    args.log.info('Adding nodes to the graph')
    G = nx.Graph()
    for concept in args.api.db.iter_concepts():
        G.add_node(concept.id, **concept.as_node_attrs())

    args.log.info('Adding edges to the graph')
    for v_, forms in tqdm(args.api.db.iter_wordlists(varieties), total=len(varieties), leave=False):
        cols = full_colexification(forms)

        for k, v in cols.items():
            for formA, formB in combinations(v, r=2):
                # check for identical concept resulting from word-variants
                if formA.concepticon_id != formB.concepticon_id:
                    words[formA.gid] = [formA.clics_form, formA.form]
                    if not G[formA.concepticon_id].get(formB.concepticon_id, False):
                        G.add_edge(
                            formA.concepticon_id,
                            formB.concepticon_id,
                            words=set(),
                            languages=set(),
                            families=set(),
                            wofam=[],
                        )

                    G[formA.concepticon_id][formB.concepticon_id]['words'].add(
                        (formA.gid, formB.gid))
                    G[formA.concepticon_id][formB.concepticon_id]['languages'].add(v_.gid)
                    G[formA.concepticon_id][formB.concepticon_id]['families'].add(v_.family)
                    G[formA.concepticon_id][formB.concepticon_id]['wofam'].append('/'.join([
                        formA.gid,
                        formB.gid,
                        formA.clics_form,
                        v_.gid,
                        v_.family,
                        clean(formA.form),
                        clean(formB.form)]))
    args.api.json_dump(words, 'app', 'source', 'words.json')

    edges = {}
    for edgeA, edgeB, data in G.edges(data=True):
        edges[edgeA, edgeB] = (len(data['families']), len(data['languages']), len(data['words']))

    ignore_edges = []
    for edgeA, edgeB, data in G.edges(data=True):
        data['WordWeight'] = len(data['words'])
        data['words'] = ';'.join(sorted(['{0}/{1}'.format(x, y) for x, y in data['words']]))
        data['FamilyWeight'] = len(data['families'])
        data['families'] = ';'.join(sorted(data['families']))
        data['LanguageWeight'] = len(data['languages'])
        data['languages'] = ';'.join(data['languages'])
        data['wofam'] = ';'.join(data['wofam'])
        if edgefilter == 'families' and data['FamilyWeight'] < threshold:
            ignore_edges.append((edgeA, edgeB))
        elif edgefilter == 'languages' and data['LanguageWeight'] < threshold:
            ignore_edges.append((edgeA, edgeB))
        elif edgefilter == 'words' and data['WordWeight'] < threshold:
            ignore_edges.append((edgeA, edgeB))

    G.remove_edges_from(ignore_edges)

    nodenames = {r[0]: r[1] for r in args.api.db.fetchall(
        "select distinct concepticon_id, concepticon_gloss from parametertable")}

    table = Table('ID A', 'Concept A', 'ID B', 'Concept B', 'Families', 'Languages', 'Words')
    count = 0
    for (nodeA, nodeB), (fc, lc, wc) in sorted(edges.items(), key=lambda i: i[1], reverse=True):
        if (nodeA, nodeB) not in ignore_edges:
            table.append([nodeA, nodenames[nodeA], nodeB, nodenames[nodeB], fc, lc, wc])
            count += 1
        if count >= 10:
            break
    print(table.render(tablefmt='simple'))

    args.api.save_graph(G, args.graphname or 'network', threshold, edgefilter)


@command('articulation-points')
def articulationpoints(args):
    """Compute articulation points in subgraphs of the graph.

    Parameters
    ----------
    graphname : str
        Refers to pre-computed graphs stored in folder, with the name being the
        first element.
    edgefilter : str (default="families")
        Refers to second component of filename, thus, the component managing
        how edges are created and defined (here: language families as a
        default).
    subgraph : str (default="infomap")
        Determines the name of the subgraph that is used to pre-filter the
        search for articulation points. Defaults to the infomap-algorithms.
    threshold : int (default=1)
        The threshold which was used to calculate the community detection
        analaysis.

    Note
    ----
    Method searches for articulation points inside partitions of the graph,
    usually the partitions as provided by the infomap algorithm. The repository
    stores graph data in different forms, as binary graph and as gml, and the
    paramters are used to identify a given analysis by its filename and make
    sure the correct graph is loaded.
    """
    args.api._log = args.log
    threshold = args.threshold or 1

    graph = args.api.load_graph('infomap', threshold, args.edgefilter)
    coms = defaultdict(list)
    for node, data in graph.nodes(data=True):
        coms[data['infomap']].append(node)
    for com, nodes in sorted(coms.items(), key=lambda x: len(x), reverse=True):
        if len(nodes) > 5:
            subgraph = graph.subgraph(nodes)
            degrees = subgraph.degree(list(subgraph.nodes()))
            cnode = [a for a, b in sorted(degrees, key=lambda x: x[1], reverse=True)][0]
            graph.node[cnode]['DegreeCentrality'] = 1
            for artip in nx.articulation_points(subgraph):
                graph.node[artip]['ArticulationPoint'] = \
                    graph.node[artip].get('ArticulationPoint', 0) + 1
                if bool(args.verbosity):
                    print('{0}\t{1}\t{2}'.format(
                        com, graph.node[cnode]['Gloss'], graph.node[artip]['Gloss']))

    for node, data in graph.nodes(data=True):
        data.setdefault('ArticulationPoint', 0)
        data.setdefault('DegreeCentrality', 0)

    args.api.save_graph(graph, 'articulationpoints', threshold, args.edgefilter)


@command()
def subgraph(args, neighbor_weight=None):
    args.api._log = args.log
    graphname = args.graphname or 'network'
    threshold = args.threshold or 1
    edgefilter = args.edgefilter
    neighbor_weight = neighbor_weight or 5

    _graph = args.api.load_graph(graphname, threshold, edgefilter)
    for node, data in _graph.nodes(data=True):
        generations = [{node}]
        while generations[-1] and len(set.union(*generations)) < 30 and len(generations) < 3:
            nextgen = set.union(*[set(_graph[n].keys()) for n in generations[-1]])
            if len(nextgen) > 50:
                break  # pragma: no cover
            else:
                generations.append(set.union(*[set(_graph[n].keys()) for n in generations[-1]]))
        data['subgraph'] = list(set.union(*generations))

    args.api.save_graph(_graph, 'subgraph', threshold, edgefilter)

    outdir = args.api.existing_dir('app', 'subgraph', clean=True)
    cluster_names = {}
    nodes2cluster = {}
    nidx = 1
    for node, data in tqdm(
            sorted(_graph.nodes(data=True), key=lambda x: len(x[1]['subgraph']), reverse=True),
            leave=False):
        nodes = tuple(sorted(data['subgraph']))
        sg = _graph.subgraph(data['subgraph'])
        if nodes not in nodes2cluster:
            d_ = sorted(sg.degree(), key=lambda x: x[1], reverse=True)
            d = [_graph.node[a]['Gloss'] for a, b in d_][0]
            nodes2cluster[nodes] = 'subgraph_{0}_{1}'.format(nidx, d)
            nidx += 1
        cluster_name = nodes2cluster[nodes]
        data['ClusterName'] = cluster_name
        for n, d in sg.nodes(data=True):
            d['OutEdge'] = []
            neighbors = [
                n_ for n_ in _graph if
                n_ in _graph[node] and
                _graph[node][n_]['FamilyWeight'] >= neighbor_weight and
                n_ not in sg]
            if neighbors:
                sg.node[node]['OutEdge'] = []
                for n_ in neighbors:
                    sg.node[node]['OutEdge'].append([
                        'subgraph_' + n_ + '_' + _graph.node[n]['Gloss'],
                        _graph.node[n_]['Gloss'],
                        _graph.node[n_]['Gloss'],
                        _graph[node][n_]['FamilyWeight'],
                        n_
                    ])
                    sg.node[node]['OutEdge'].append([
                        _graph.node[n]['ClusterName'],
                        _graph.node[n]['CentralConcept'],
                        _graph.node[n]['Gloss'],
                        _graph[node][n]['WordWeight'],
                        n
                    ])
        if len(sg) > 1:
            jsonlib.dump(
                json_graph.adjacency_data(sg), outdir / (cluster_name + '.json'), sort_keys=True)
            cluster_names[data['Gloss']] = cluster_name

    for node, data in _graph.nodes(data=True):
        if 'OutEdge' in data:
            data['OutEdge'] = '//'.join([str(x) for x in data['OutEdge']])
    args.api.write_js_var('SUBG', cluster_names, 'app', 'source', 'subgraph-names.js')


@command()
def communities(args, neighbor_weight=None):
    graphname = args.graphname or 'network'
    edge_weights = args.weight
    vertex_weights = str('FamilyFrequency')
    normalize = args.normalize
    edgefilter = args.edgefilter
    threshold = args.threshold or 1
    neighbor_weight = neighbor_weight or 5

    _graph = args.api.load_graph(graphname, threshold, edgefilter)
    args.log.info('loaded graph')
    for n, d in tqdm(_graph.nodes(data=True), desc='vertex-weights', leave=False):
        d[vertex_weights] = int(d[vertex_weights])

    if normalize:
        for edgeA, edgeB, data in tqdm(_graph.edges(data=True), desc='normalizing', leave=False):
            data[str('weight')] = data[edge_weights] ** 2 / (
                _graph.node[edgeA][vertex_weights] +
                _graph.node[edgeB][vertex_weights] -
                data[edge_weights])
        vertex_weights = None
        edge_weights = 'weight'
        args.log.info('computed weights')

    graph = networkx2igraph(_graph)
    args.log.info('starting infomap')
    args.log.info('converted graph...')

    comps = graph.community_infomap(
        edge_weights=str(edge_weights), vertex_weights=vertex_weights)

    args.log.info('finished infomap')
    D, Com = {}, defaultdict(list)
    for i, comp in enumerate(sorted(comps.subgraphs(), key=lambda x: len(x.vs), reverse=True)):
        for vertex in [v['name'] for v in comp.vs]:
            D[graph.vs[vertex]['ConcepticonId']] = str(i + 1)
            Com[i + 1].append(graph.vs[vertex]['ConcepticonId'])

    for node, data in _graph.nodes(data=True):
        data['infomap'] = D[node]
        data['ClusterName'] = ''
        data['CentralConcept'] = ''

    # get the articulation points etc. immediately
    for idx, nodes in sorted(Com.items()):
        sg = _graph.subgraph(nodes)
        if len(sg) > 1:
            d_ = sorted(sg.degree(), key=lambda x: x[1], reverse=True)
            d = [_graph.node[a]['Gloss'] for a, b in d_][0]
            cluster_name = 'infomap_{0}_{1}'.format(idx, d)
        else:
            d = _graph.node[nodes[0]]['Gloss']
            cluster_name = 'infomap_{0}_{1}'.format(idx, _graph.node[nodes[0]]['Gloss'])
        args.log.debug(cluster_name, d)
        for node in nodes:
            _graph.node[node]['ClusterName'] = cluster_name
            _graph.node[node]['CentralConcept'] = d

    args.log.info('computed cluster names')

    cluster_dir = args.api.existing_dir('app', 'cluster', clean=True)
    cluster_names = {}
    removed = []
    for idx, nodes in tqdm(sorted(Com.items()), desc='export to app', leave=False):
        sg = _graph.subgraph(nodes)
        for node, data in sg.nodes(data=True):
            data['OutEdge'] = []
            neighbors = [
                n for n in _graph if
                n in _graph[node] and
                _graph[node][n]['FamilyWeight'] >= neighbor_weight and
                n not in sg]
            if neighbors:
                sg.node[node]['OutEdge'] = []
                for n in neighbors:
                    sg.node[node]['OutEdge'].append([
                        _graph.node[n]['ClusterName'],
                        _graph.node[n]['CentralConcept'],
                        _graph.node[n]['Gloss'],
                        _graph[node][n]['WordWeight'],
                        n
                    ])
        if len(sg) > 1:
            jsonlib.dump(
                json_graph.adjacency_data(sg),
                cluster_dir / (_graph.node[nodes[0]]['ClusterName'] + '.json'),
                sort_keys=True)
            for node in nodes:
                cluster_names[_graph.node[node]['Gloss']] = _graph.node[node]['ClusterName']
        else:
            removed += [list(nodes)[0]]
    _graph.remove_nodes_from(removed)
    for node, data in _graph.nodes(data=True):
        if 'OutEdge' in data:
            data['OutEdge'] = '//'.join(['/'.join([str(y) for y in x]) for x in data['OutEdge']])
    removed = []
    for nA, nB, data in tqdm(_graph.edges(data=True), desc='remove edges', leave=False):
        if _graph.node[nA]['infomap'] != _graph.node[nB]['infomap'] and data['FamilyWeight'] < 5:
            removed += [(nA, nB)]
    _graph.remove_edges_from(removed)

    args.api.save_graph(_graph, 'infomap', threshold, edgefilter)
    args.api.write_js_var('INFO', cluster_names, 'app', 'source', 'infomap-names.js')


@command('graph-stats')
def graph_stats(args):
    nw = args.api.load_network(args.graphname or 'network', args.threshold or 1, args.edgefilter)
    graph = nw.graph
    print(tabulate([
        ['nodes', len(graph)],
        ['edges', len(graph.edges())],
        ['components', len(nw.components(graph))],
        ['communities', len(nw.communities(graph))]
    ]))
