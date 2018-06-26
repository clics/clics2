# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict
from itertools import combinations
import os
import json
import sqlite3

import geojson
from clldutils.clilib import command
from clldutils.path import Path, rmtree, write_text
from clldutils.markup import Table
from clldutils.misc import nfilter
from clldutils import jsonlib
from pyconcepticon.api import Concepticon
from pyglottolog.api import Glottolog
from pylexibank.dataset import iter_datasets
from lingpy.convert.graph import networkx2igraph
import networkx as nx
from networkx.readwrite import json_graph
from tabulate import tabulate

from pyclics.util import full_colexification, pb
from pyclics.api import Network


@command('list')
def list_(args):
    """List datasets available for loading

    clics --lexibank-repos=PATH/TO/lexibank-data list
    """
    if args.unloaded:
        i = 0
        for i, ds in enumerate(iter_datasets()):
            print(ds.cldf_dir)
        if not i:
            print('No datasets installed')
    else:
        table = Table('#', 'dataset', 'concepts', 'varieties', 'languages')
        try:
            concept_counts = dict(args.api.db.fetchall('conceptsets_by_dataset'))
        except sqlite3.OperationalError:
            print('No datasets loaded yet')
            return
        var_counts = dict(args.api.db.fetchall('varieties_by_dataset'))
        gc_counts = dict(args.api.db.fetchall('glottocodes_by_dataset'))
        for count, d in enumerate(args.api.db.datasets):
            table.append([
                count + 1,
                d,
                concept_counts[d],
                var_counts[d],
                gc_counts[d],
            ])
        table.append([
            '',
            'TOTAL',
            args.api.db.fetchone(
                "select count(distinct concepticon_id) from parametertable")[0],
            args.api.db.fetchone(
                "select count(*) from languagetable")[0],
            args.api.db.fetchone(
                "select count(distinct glottocode) from languagetable")[0],
        ])
        print(table.render(tablefmt='simple'))


@command()
def load(args):
    """
    clics load
    """
    args.api.db.create(exists_ok=True)
    in_db = args.api.db.datasets
    for ds in iter_datasets():
        if args.unloaded and ds.id in in_db:
            args.log.info('skipping {0} - already loaded'.format(ds.id))
            continue
        args.log.info('loading {0}'.format(ds.id))
        args.api.db.load(ds)
    args.log.info('loading Concepticon data')
    args.api.db.load_concepticon_data(Concepticon(args.concepticon_repos))
    args.log.info('loading Glottolog data')
    args.api.db.load_glottolog_data(Glottolog(args.glottolog_repos))
    return


@command()
def clean(args):
    """Removes all loaded lexical data

    clics clean
    """
    args.api.db.drop()


@command()
def languages(args):
    varieties = []
    ltable = Table('Number', 'Language', 'Family', 'Size', 'Source')
    gcodes = set()
    i = 0

    with args.api.csv_writer(Path('output', 'stats'), 'languages') as writer:
        for i, var in enumerate(args.api.db.iter_varieties()):
            if i == 0:
                writer.writerow(list(var.as_stats_dict().keys()))
            varieties.append(var)
            gcodes.add(var.glottocode)
            writer.writerow(list(var.as_stats_dict().values()))
            ltable.append([
                i + 1,
                '[{0}](http://glottolog.org/resource/languoid/id/{1})'.format(
                    var.name, var.glottocode),
                var.family
                if var.family != var.glottocode else 'isolate',
                var.size,
                var.source
            ])

    #
    # FIXME: write requirements.txt!
    #
    args.api.write_md_table('datasets', 'README', 'Languages in CLICS', ltable, args.log)
    args.api.write_md_table('output', 'languages', 'Languages in CLICS', ltable, args.log)

    lgeo = geojson.FeatureCollection(nfilter(v.as_geojson() for v in varieties))
    jsonlib.dump(lgeo, args.api.path('output', 'languages.geojson'), indent=2)
    jsonlib.dump(lgeo, args.api.path('app', 'source', 'langsGeo.json'), indent=2)
    if args.verbosity:
        print('Found {0} languages ({1} unique glottocodes)'.format(i + 1, len(gcodes)))


@command()
def concepts(args):
    concepts = defaultdict(list)
    ambiguous_concept_mapping = set()

    with args.api.csv_writer(Path('output', 'data'), 'words') as writer:
        writer.writerow([
            'WordID',
            'ConcepticonId',
            'ConcepticonGloss',
            'Gloss',
            'LanguageId',
            'LanguageName',
            'Family',
            'Value',
            'ClicsValue'])

        for v, forms in pb(args.api.db.iter_wordlists()):
            visited = {}

            for form in forms:
                if form.concepticon_id in visited and visited[form.concepticon_id] != form.gloss:
                    # The concept was already seen, but with a different gloss!
                    ambiguous_concept_mapping.add((
                        v.gid,
                        form.concepticon_id,
                        form.gloss,
                        visited[form.concepticon_id]))
                    continue

                concepts[form.concepticon_id].append((v.family, v.gid, form.gid))
                writer.writerow([
                    form.gid,
                    form.concepticon_id,
                    form.concepticon_gloss,
                    form.gloss,
                    v.glottocode,
                    v.name,
                    v.family,
                    form.form,
                    form.clics_form])
                visited[form.concepticon_id] = form.gloss

    for am in ambiguous_concept_mapping:
        args.log.warn('{0} {1} is linked from different glosses {2} and {3}'.format(*am))

    concept_table = Table('Number', 'Concept', 'SemanticField', 'Category', 'Reflexes')
    with args.api.csv_writer(Path('output', 'stats'), 'concepts') as writer:
        for i, concept in enumerate(args.api.db.iter_concepts()):
            if i == 0:
                writer.writerow(list(concept.asdict().keys()))
            writer.writerow(list(concept.asdict().values()))
            concept_table.append([
                i + 1,
                '[{0}](http://concepticon.clld.org/parameters/{1})'.format(
                    concept.gloss, concept.id),
                concept.semantic_field,
                concept.ontological_category,
                len(concept.forms)])

    args.api.write_md_table(
        'output', 'concepts', 'Concepts in CLICS', concept_table, args.log)
    if args.verbose:
        print(len(concepts))
    return concepts


@command()
def colexification(args):
    threshold = args.threshold or 1
    edgefilter = args.edgefilter
    words = {}
    
    def clean(word):
        return ''.join([w for w in word if w not in '/,;"'])

    G = nx.Graph()
    for concept in args.api.db.iter_concepts():
        G.add_node(concept.id, **concept.as_node_attrs())

    for v_, forms in pb(args.api.db.iter_wordlists()):
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

                    G[formA.concepticon_id][formB.concepticon_id]['words'].add((formA.gid, formB.gid))
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

    ignore_edges = []
    with args.api.csv_writer(Path('output', 'stats'), 'colexifications-{0}-{1}'.format(
            threshold, edgefilter)) as f:
        f.writerow('EdgeA,EdgeB,FamilyWeight,LanguageWeight,WordWeight'.split())
        for edgeA, edgeB, data in G.edges(data=True):
            data['WordWeight'] = len(data['words'])
            data['words'] = ';'.join(
                sorted(['{0}/{1}'.format(x, y) for x, y in data['words']]))
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
            f.writerow([
                '{0}'.format(x) for x in [
                    edgeA,
                    edgeB,
                    data['FamilyWeight'],
                    data['LanguageWeight'],
                    data['WordWeight']]])

    G.remove_edges_from(ignore_edges)
    args.api.save_graph(
        G, args.graphname or 'network', threshold, edgefilter, log=args.log)
    jsonlib.dump(words, args.api.path('app', 'source', 'words.json'), indent=2)


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
    threshold = args.threshold or 1
    graphname = args.graphname or 'network'

    graph = args.api.load_graph(graphname, threshold, args.edgefilter)
    coms = defaultdict(list)
    for node, data in graph.nodes(data=True):
        coms[data['infomap']].append(node)
    _tmp = []
    for com, nodes in sorted(coms.items(), key=lambda x: len(x), reverse=True):
        if len(nodes) > 5:
            subgraph = graph.subgraph(nodes)
            degrees = subgraph.degree(list(subgraph.nodes()))
            cnodes = [a for a, b in sorted(degrees, key=lambda x:
                x[1], reverse=True)]
            cnode = cnodes[0]
            graph.node[cnode]['DegreeCentrality'] = 1
            artipoints = nx.articulation_points(subgraph)
            for artip in artipoints:
                if 'ArticulationPoint' in graph.node[artip]:
                    graph.node[artip]['ArticulationPoint'] += 1
                else:
                    graph.node[artip]['ArticulationPoint'] = 1
                if bool(args.verbosity):
                    print('{0}\t{1}\t{2}'.format(
                        com, graph.node[cnode]['Gloss'], graph.node[artip]['Gloss']))
                _tmp.append((
                    artip, graph.node[artip]['Gloss'],
                    com,
                    cnode,
                    graph.node[cnode]['Gloss'],
                    len(nodes)))
            if bool(args.verbosity):
                print('')
    for node, data in graph.nodes(data=True):
        data.setdefault('ArticulationPoint', 0)
        data.setdefault('DegreeCentrality', 0)

    aps = Network('articulationpoints', threshold, args.edgefilter)
    ap_table = Table('Number', 'Concept', 'Community', 'CommunitySize', 'CentralNode')
    with args.api.csv_writer('stats', '{0}'.format(aps)) as writer:
        writer.writerow([
            'ConcepticonId',
            'ConcepticonGloss',
            'Community',
            'CentralNode',
            'CentralNodeGloss',
            'CommunitySize',
            ])
        for i, line in enumerate(_tmp):
            writer.writerow(line)
            ap_table.append([
                i + 1,
                '[{0[1]}]({0[0]})'.format(line),
                line[2],
                line[5],
                '[{0[4]}]({0[3]})'.format(line)])

    args.api.write_md_table(
        'stats',
        '{0}'.format(aps),
        'Articulation Points (Analysis {0} / {1})'.format(threshold, args.edgefilter),
        ap_table,
        args.log)
    args.api.save_graph(graph, aps, log=args.log)


@command()
def subgraph(args):
    graphname = args.graphname or 'network'
    edge_weights = args.weight
    threshold = args.threshold or 1
    edgefilter = args.edgefilter

    _graph = args.api.load_graph(graphname, threshold, edgefilter)
    for node, data in _graph.nodes(data=True):
        data['subgraph'] = [node]

    for node, data in _graph.nodes(data=True):
        max_gen = 1
        min_weight = 3
        queue = [(node, _graph[node], 0)]
        while queue:
            source, neighbors, generation = queue.pop(0)
            for n, d in neighbors.items():
                if n not in data['subgraph'] and d[edge_weights] > min_weight:
                    data['subgraph'] += [n]
                    queue += [(n, _graph[n], generation+1)]
            if generation > max_gen:
                if len(data['subgraph']) < 8:
                    max_gen += 1
                    min_weight -= 1
                else:
                    break
            if len(data['subgraph']) > 30:
                break
        args.log.info('{0:20} {1:20} {2}'.format(
            node, data['Gloss'], len(data['subgraph'])))

    outdir = args.api.path('app', 'subgraph')
    if outdir.exists():
        rmtree(outdir)
        args.log.info('removed nodes')
    outdir.mkdir()

    cluster_names = {}
    nodes2cluster = {}
    nidx = 1
    duplicates = []
    for node, data in pb(sorted(
            _graph.nodes(data=True),
            key=lambda x: len(x[1]['subgraph']), reverse=True),
        desc='preparing nodes'
    ):
        nodes = tuple(sorted(data['subgraph']))
        sg = _graph.subgraph(nodes)
        if nodes not in nodes2cluster:
            d_ = sorted(sg.degree(), key=lambda x: x[1], reverse=True)
            d = [_graph.node[a]['Gloss'] for a, b in d_][0]
            nodes2cluster[nodes] = 'subgraph_{0}_{1}'.format(nidx, d)
            nidx += 1
        else:
            duplicates.append(nodes)
        cluster_name = nodes2cluster[nodes]
        data['ClusterName'] = cluster_name
        for n, d in sg.nodes(data=True):
            d['OutEdge'] = []
            neighbors = [
                n_ for n_ in _graph if
                n_ in _graph[node] and
                _graph[node][n_]['FamilyWeight'] >= 5 and
                n_ not in sg]
            if neighbors:
                sg.node[node]['OutEdge'] = []
                for n_ in neighbors:
                    sg.node[node]['OutEdge'] += [[
                        'subgraph_'+n_+'_'+_graph.node[n]['Gloss'],
                        _graph.node[n_]['Gloss'],
                        _graph.node[n_]['Gloss'],
                        _graph[node][n_]['FamilyWeight'],
                        n_
                        ]]
                    sg.node[node]['OutEdge'] += [[
                        _graph.node[n]['ClusterName'],
                        _graph.node[n]['CentralConcept'],
                        _graph.node[n]['Gloss'],
                        _graph[node][n]['WordWeight'],
                        n
                        ]]
        if len(sg) > 1:
            jsonlib.dump(
                json_graph.adjacency_data(sg),
                args.api.path('app', 'subgraph', cluster_name+'.json'),
                sort_keys=True)
            cluster_names[data['Gloss']] = cluster_name

    for nodes in duplicates:
        args.log.info('Duplicate node: {0}'.format(nodes))

    for node, data in _graph.nodes(data=True):
        if 'OutEdge' in data:
            data['OutEdge'] = '//'.join([str(x) for x in data['OutEdge']])
    write_text(
        args.api.path('app', 'source', 'subgraph-names.js'),
        'var SUBG = ' + json.dumps(cluster_names, indent=2) + ';')
    args.api.save_graph(_graph, 'subgraph', threshold, edgefilter, log=args.log)


@command()
def communities(args):
    graphname = args.graphname or 'network'
    edge_weights = args.weight
    vertex_weights = str('FamilyFrequency')
    verbose = bool(args.verbose)
    normalize = args.normalize
    edgefilter = args.edgefilter
    threshold = args.threshold or 1

    _graph = args.api.load_graph(graphname, threshold, edgefilter)
    args.log.info('loaded graph')
    for n, d in pb(_graph.nodes(data=True), desc='vertex-weights'):
        d[vertex_weights] = int(d[vertex_weights])

    if normalize:
        for edgeA, edgeB, data in pb(_graph.edges(data=True), desc='normalizing'):
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
    with args.api.csv_writer(Path('output', 'communities'), 'infomap') as writer:
        for i, comp in enumerate(sorted(comps.subgraphs(), key=lambda x:
            len(x.vs), reverse=True)):
            vertices = [v['name'] for v in comp.vs]
            for vertex in vertices:
                if verbose: print(graph.vs[vertex]['Gloss'], i+1)
                D[graph.vs[vertex]['ConcepticonId']] = str(i+1)
                Com[i+1] += [graph.vs[vertex]['ConcepticonId']]
                writer.writerow([
                    graph.vs[vertex]['ConcepticonId'],
                    graph.vs[vertex]['Gloss'],
                    i + 1])
            if verbose: print('---')
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
            cluster_name = 'infomap_{0}_{1}'.format(idx,
                    _graph.node[nodes[0]]['Gloss'])
        args.log.debug(cluster_name, d)
        for node in nodes:
            _graph.node[node]['ClusterName'] = cluster_name
            _graph.node[node]['CentralConcept'] = d

    args.log.info('computed cluster names')
    
    cluster_names = {}
    cluster_dir = args.api.path('app', 'cluster')
    if cluster_dir.exists():
        rmtree(cluster_dir)
        args.log.info('removed nodes')
        cluster_dir.mkdir()

    removed = []
    for idx, nodes in pb(sorted(Com.items()), desc='export to app'):
        sg = _graph.subgraph(nodes)
        for node, data in sg.nodes(data=True):
            data['OutEdge'] = []
            neighbors = [n for n in _graph if n in _graph[node] and
                    _graph[node][n]['FamilyWeight'] >= 5 and n not in sg]
            if neighbors:
                sg.node[node]['OutEdge'] = []
                for n in neighbors:
                    sg.node[node]['OutEdge'] += [[
                        _graph.node[n]['ClusterName'],
                        _graph.node[n]['CentralConcept'],
                        _graph.node[n]['Gloss'],
                        _graph[node][n]['WordWeight'],
                        n
                        ]]
        if len(sg) > 1:
            jsonlib.dump(
                    json_graph.adjacency_data(sg),
                    args.api.path(
                        'app', 
                        'cluster', 
                        _graph.node[nodes[0]]['ClusterName']+'.json'
                        ),
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
    for nA, nB, data in pb(_graph.edges(data=True), desc='remove edges'):
        if _graph.node[nA]['infomap'] != _graph.node[nB]['infomap'] and data['FamilyWeight'] < 5:
            removed += [(nA, nB)]
    _graph.remove_edges_from(removed)

    args.api.save_graph(_graph, 'infomap', threshold, edgefilter, log=args.log)
    with open(args.api.path('app', 'source', 'infomap-names.js').as_posix(), 'w') as f:
        f.write('var INFO = '+json.dumps(cluster_names, indent=2)+';')


@command()
def export(args):
    threshold = args.threshold or 1
    edgefilter = args.edgefilter
    nG = args.api.load_graph('network', threshold, edgefilter)
    iG = args.api.load_graph('infomap', threshold, edgefilter)
    sG = args.api.load_graph('subgraph', threshold, edgefilter)

    with args.api.csv_writer(Path('output', 'clld'), 'edges') as writer:
        writer.writerow(['id', 'node_a', 'node_b', 'weight'])

        for node_a, node_b, data in iG.edges(data=True):
            edge_id = node_a + '/' + node_b
            writer.writerow([edge_id, node_a, node_b, data.get('weight')])

    with args.api.csv_writer(Path('output', 'clld'), 'colexifications') as writer:
        writer.writerow([
            'id',
            'word_a',
            'word_b',
            'clics_value',
            'language_id',
            'family',
            'value_a',
            'value_b'])
        for nodeA, nodeB, data in nG.edges(data=True):
            for word in data['wofam'].split(';'):
                w1, w2, entry, lid, fam, ovalA, ovalB = word.split('/')
                writer.writerow([w1+'/'+w2, w1, w2, entry, lid, fam, ovalA, ovalB])
    
    visited = set()
    with args.api.csv_writer(Path('output', 'clld'), 'graphs') as writer:
        writer.writerow(['id', 'nodes', 'type'])
        for node, data in iG.nodes(data=True):
            if data['ClusterName'] not in visited:
                nodes = sorted(
                    n for n in iG if iG.node[n]['ClusterName'] == data['ClusterName'])
                writer.writerow([data['ClusterName'], '/'.join(nodes), 'infomap'])
                visited.add(data['infomap'])
        for node, data in sG.nodes(data=True):
            if data['ClusterName'] not in visited:
                nodes = sorted(data['subgraph'])
                writer.writerow([data['ClusterName'], '/'.join(nodes), 'subgraph'])
                visited.add(data['ClusterName'])


@command('graph-stats')
def graph_stats(args):
    graphname = args.graphname or 'network'
    edgefilter = args.edgefilter
    threshold = args.threshold or 1
    nw = args.api.load_network(graphname, threshold, edgefilter)
    comps = len(nw.components())
    comms = len(nw.communities())
    table = [['nodes', len(nw.G)]]
    table += [['edges', len(nw.G.edges())]]
    table += [['components', comps]]
    table += [['communities', comms]]
    print(tabulate(table))
