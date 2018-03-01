# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict
from itertools import combinations
import os

from six import PY2
from clldutils.clilib import command
from clldutils.path import write_text, Path, rmtree
from clldutils.markup import Table
from clldutils import jsonlib
from pyconcepticon.api import Concepticon
from pyglottolog.api import Glottolog
from lingpy.convert.graph import networkx2igraph
import networkx as nx
from networkx.readwrite import json_graph
from tabulate import tabulate
import json

from pyclics.util import (
    load_concepticon, full_colexification, make_language_map, partial_colexification,
    clics_path, pb
)
from pyclics.api import Network


@command('list')
def list_(args):
    """List datasets available for loading

    clics --lexibank-repos=PATH/TO/lexibank-data list
    """
    if args.unloaded:
        for d in sorted(args.lexibank_repos.joinpath('datasets').iterdir()):
            if d.joinpath('cldf', 'cldf-metadata.json').exists():
                print(d.stem)
    else:
        table = [('#', 'dataset', 'concepts', 'varieties', 'languages')] 
        all_gcodes = []
        count = 1
        for d in sorted(args.api.path('datasets').iterdir()):
            if d.joinpath('md.json').exists():
                data = json.load(open(d.joinpath('md.json').as_posix()))
                gcodes = [val['glottocode'] for lid, val in data.items() if
                        lid[0] != '_']
                table += [(
                    count,
                    d.stem,
                    data['_concepts'],
                    data['_varieties'],
                    len(set(gcodes))
                    )]
                all_gcodes += gcodes
                count += 1
        table += [('', 'TOTAL', '', len(all_gcodes), len(set(all_gcodes)))]
        print(tabulate(table, headers='firstrow'))

@command()
def load(args):
    """
    clics load [DATASET]+
    """
    languoids = {}
    for l in pb(Glottolog(args.glottolog_repos).languoids(), 
            desc='loading glottolog', total=25000):
        languoids[l.id] = l
    args.log.info('{0:25} | {1:10} | {2:10} | {3:10} | {4:5}'.format(
        'datasets', 'wordlists', 'lexemes', 'concepts', 'glottocodes'))
    args.log.info('{0:25} | {1:10} | {2:10} | {3:10} | {4:5}'.format(
        '---', '---', '---', '---', '---'))
    for ds in args.args:
        ds = args.api.path('cldf', ds) 
        res, gcodes, concepts = args.api.load(ds, languoids)
        args.log.info(
                '{0:25} | {1:10} | {2:10} | {3:10} | {4:5}'.format(
            ds.name, len(res), sum(res.values()), concepts, gcodes))


@command()
def clean(args):
    """Removes all loaded lexical data

    clics clean
    """
    for p in args.api.path('datasets').iterdir():
        if not (args.args or p.name in args.args) and p.name not in [
                'datasets.csv', 'README.md', 'sources.bib'] and p.is_dir():
            rmtree(p)


@command()
def languages(args):
    data = {}
    ltable = Table('Number', 'Language', 'Family', 'Size', 'Source')
    gcodes = defaultdict(list)
    with args.api.csv_writer(Path('output', 'stats'), 'languages') as writer:
        writer.writerow([
            'Identifier',
            'Language_name',
            'Language_ID',
            'Family',
            'Longitude',
            'Latitude'])
        count = 1
        for i, wl in pb(enumerate(args.api.wordlists()), desc='loading wordlists'):
            data[wl['meta']['identifier']] = wl['meta']
            gcodes[wl['meta']['glottocode']] += [(wl['meta']['identifier'], 
                wl['meta']['size'])]
            writer.writerow([
                wl['meta']['identifier'],
                wl['meta']['name'],
                wl['meta']['glottocode'],
                wl['meta']['family'],
                wl['meta']['longitude'],
                wl['meta']['latitude']])
            ltable.append([
                i + 1,
                '[{0}](http://glottolog.org/resource/languoid/id/{1})'.format(
                    wl['meta']['name'], wl['meta']['glottocode']),
                wl['meta']['family']
                if wl['meta']['family'] != wl['meta']['glottocode'] else 'isolate',
                wl['meta']['size'],
                wl['meta']['source'],
            ])
            count += 1

    args.api.write_md_table('datasets', 'README', 'Languages in CLICS', ltable, args.log)
    args.api.write_md_table('output', 'languages', 'Languages in CLICS', ltable, args.log)
    jsonlib.dump(make_language_map(data), args.api.path('output',
        'languages.geojson'), indent=2)
    jsonlib.dump(make_language_map(data), args.api.path('app', 'source',
        'langsGeo.json'),
            indent=2)
    if args.verbose:
        print('Found {0} languages ({1} unique glotto codes)'.format(
            count-1, len(gcodes)))


@command()
def concepts(args):
    concepticon = load_concepticon(args.api, Concepticon(args.concepticon_repos))
    concepts = defaultdict(list)
    languages = [line[0] for line in args.api.csv_reader(Path('output',
        'stats'), 'languages')]

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
        all_visited = set()
        for wl in pb(args.api.wordlists(), desc='counting concepts'):
            if wl['meta']['identifier'] in languages and \
                    wl['meta']['longitude'] and wl['meta']['family'] != 'Bookkeeping':
                visited = defaultdict(list)
                cidx, vidx, oidx, gidx = (
                    wl[0].index('Parameter_ID'),
                    wl[0].index('Clics_Value'),
                    wl[0].index('Value'),
                    wl[0].index('Parameter_name'))
                for idx in wl['identifiers']:
                    concept = wl[idx][cidx]
                    value = wl[idx][vidx]
                    gloss = wl[idx][gidx]                    
                    if concept and gloss == visited.get(concept, gloss) and concepticon.get(concept, {}).get('gloss', ''):
                        concepts[concept].append(
                            (wl['meta']['family'], wl['meta']['identifier'], idx))
                        writer.writerow([
                            idx,
                            concept,
                            concepticon[concept]['gloss'],
                            wl[idx][gidx],
                            wl['meta']['glottocode'],
                            wl['meta']['name'],
                            wl['meta']['family'],
                            wl[idx][oidx],
                            value])
                        visited[concept] = gloss
                    else:
                        pair = (concept, gloss, visited[concept])
                        if pair not in all_visited:
                            args.log.warn('Problem: {0:20} {1:20} {2:20} {3}'.format(concept, gloss, visited[concept],
                                    wl['meta']['source']))
                            all_visited.add(pair)
                        else:
                            pass

    concept_table = Table('Number', 'Concept', 'SemanticField', 'Category', 'Reflexes')
    with args.api.csv_writer(Path('output', 'stats'), 'concepts') as writer:
        writer.writerow([
            'ID',
            'Gloss',
            'Semanticfield',
            'Category',
            'WordFrequency',
            'LanguageFrequency',
            'FamilyFrequency',
            'Words',
            'Languages',
            'Families',
        ])
        for i, (concept, lists) in enumerate(concepts.items()):
            writer.writerow([
                concept,
                concepticon[concept]['gloss'],
                concepticon[concept]['semanticfield'],
                concepticon[concept]['ontological_category'],
                len(set([x[0] for x in lists])),
                len(set([x[1] for x in lists])),
                len(lists),
                ';'.join(sorted(set([x[2] for x in lists]))),
                ';'.join(sorted(set([x[1] for x in lists]))),
                ';'.join(sorted(set([x[0] for x in lists])))])
            concept_table.append([
                i + 1,
                '[{0}](http://concepticon.clld.org/parameters/{1})'.format(
                    concepticon[concept]['gloss'], concept),
                concepticon[concept]['semanticfield'],
                concepticon[concept]['ontological_category'],
                len(lists)])

    args.api.write_md_table(
        'output', 'concepts', 'Concepts in CLICS', concept_table, args.log)
    if args.verbose: print(len(concepts))
    return concepts


@command()
def colexification(args):
    threshold = args.threshold or 1
    edgefilter = args.edgefilter
    languages = [line[0] for line in args.api.csv_reader(Path('output',
        'stats'), 'languages')]
    words = {}
    
    def clean(word):
        return ''.join([w for w in word if w not in '/,;"'])

    _tmp = list(args.api.csv_reader(Path('output', 'stats'), 'concepts'))
    concepts = {x[0]: dict(zip(_tmp[0], x)) for x in _tmp[1:]}
    G = nx.Graph()
    for idx, vals in concepts.items():
        vals['ConcepticonId'] = vals['ID']
        G.add_node(idx, **vals)

    for wl in pb(args.api.wordlists(), desc='iterating wordlists'):
        if wl['meta']['identifier'] in languages:
            cols = full_colexification(
                wl,
                key='Parameter_ID',
                entry='Clics_Value',
                indices='identifiers')
            entry_index = wl[0].index('Clics_Value')
            value_index = wl[0].index('Value')
            for k, v in cols.items():
                for (conceptA, idxA), (conceptB, idxB) in combinations(v, r=2):
                    # check for identical concept resulting from word-variants
                    if conceptA != conceptB:
                        words[idxA] = [wl[idxA][entry_index],
                                wl[idxA][value_index]]
                        if G[conceptA].get(conceptB, False):
                            G[conceptA][conceptB]['words'].add((idxA, idxB))
                            G[conceptA][conceptB]['languages'].add(wl['meta']['identifier'])
                            G[conceptA][conceptB]['families'].add(wl['meta']['family'])
                            G[conceptA][conceptB]['wofam'].append('/'.join([
                                idxA, idxB, wl[idxA][entry_index], wl['meta']['identifier'],
                                wl['meta']['family'],
                                clean(wl[idxA][value_index]),
                                clean(wl[idxB][value_index])]))
                        else:
                            G.add_edge(
                                conceptA,
                                conceptB,
                                words={(idxA, idxB)},
                                languages={wl['meta']['identifier']},
                                families={wl['meta']['family']},
                                wofam=['/'.join([idxA, idxB,
                                    wl[idxA][entry_index], wl['meta']['identifier'],
                                    wl['meta']['family'],
                                    clean(wl[idxA][value_index]),
                                    clean(wl[idxB][value_index])])]
                                )
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
    jsonlib.dump(words, args.api.path('app', 'source',
        'words.json'),
            indent=2)


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
    verbose = bool(args.verbose)
    max_gen = 2 # stops the queue
    min_weight = 4
    
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



    cluster_names = {}
    # remove json files from app
    try:
        rmtree(args.api.path('app', 'subgraph'))
        os.mkdir(args.api.path('app', 'subgraph').as_posix())
    except:
        pass

    args.log.info('removed nodes')

    nodes2cluster = {}
    nidx = 1
    for node, data in pb(sorted(_graph.nodes(data=True), key=lambda x:
            len(x[1]['subgraph']), reverse=True), desc='preparing nodes'):
        nodes = tuple(sorted(data['subgraph']))
        sg = _graph.subgraph(nodes)
        if nodes not in nodes2cluster:
            d_ = sorted(sg.degree(), key=lambda x: x[1], reverse=True)
            d = [_graph.node[a]['Gloss'] for a, b in d_][0]
            nodes2cluster[nodes] = 'subgraph_{0}_{1}'.format(
                    nidx, d)
            nidx += 1
        else:
            args.log.info('found a duplicate node')
        cluster_name = nodes2cluster[nodes]
        data['ClusterName'] = cluster_name
        for n, d in sg.nodes(data=True):
            d['OutEdge'] = [];
            neighbors = [n_ for n_ in _graph if n_ in _graph[node] and
                    _graph[node][n_]['FamilyWeight'] >= 5 and n_ not in sg]
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
                    args.api.path(
                        'app', 
                        'subgraph', 
                        cluster_name+'.json'
                        ),
                    sort_keys=True)
            cluster_names[data['Gloss']] = cluster_name
    for node, data in _graph.nodes(data=True):
        if 'OutEdge' in data:
            data['OutEdge'] = '//'.join([str(x) for x in data['OutEdge']])
    with open(args.api.path('app', 'source', 'subgraph-names.js').as_posix(), 'w') as f:
        f.write('var SUBG = '+json.dumps(cluster_names, indent=2)+';')

 
    args.api.save_graph(_graph, 'subgraph', threshold, edgefilter, log=args.log)   


@command()
def communities(args):
    graphname = args.graphname or 'network'
    edge_weights = args.weight
    vertex_weights = 'FamilyFrequency'
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
            data[b'weight' if PY2 else 'weight'] = data[edge_weights] ** 2 / (
                _graph.node[edgeA][vertex_weights] +
                _graph.node[edgeB][vertex_weights] -
                data[edge_weights])
        vertex_weights = None
        edge_weights = b'weight' if PY2 else 'weight'
        args.log.info('computed weights')

    graph = networkx2igraph(_graph)
    args.log.info('starting infomap')
    args.log.info('converted graph...')
    comps = graph.community_infomap(
        edge_weights=edge_weights, vertex_weights=vertex_weights)
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
    # remove json files from app
    try:
        rmtree(args.api.path('app', 'cluster'))
        args.log.info('removed nodes')
        os.mkdir(args.api.path('app', 'cluster').as_posix())
    except:
        pass
    
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

    # make the edges first
    with args.api.csv_writer(Path('output', 'clld'), 'edges') as writer:
        writer.writerow([
            'id',
            'node_a',
            'node_b',
            'weight'])


        for node_a, node_b, data  in iG.edges(data=True):
            edge_id = node_a + '/'+node_b
            writer.writerow([edge_id, node_a, node_b, data['weight']])
    # now make the colexifications
    with args.api.csv_writer(Path('output', 'clld'), 'colexifications') as writer:
        writer.writerow(['id', 'word_a', 'word_b', 'clics_value',
            'language_id', 'family', 'value_a', 'value_b'])
        for nodeA, nodeB, data in nG.edges(data=True):
            for word in data['wofam'].split(';'):
                w1, w2, entry, lid, fam, ovalA, ovalB = word.split('/')
                writer.writerow([w1+'/'+w2, w1, w2, entry, lid, fam, ovalA,
                    ovalB])
    
    # write the node bundles
    visited = set()
    with args.api.csv_writer(Path('output', 'clld'), 'graphs') as writer:
        writer.writerow(['id', 'nodes', 'type'])
        for node, data in iG.nodes(data=True):
            if data['ClusterName'] not in visited:
                nodes = sorted([n for n in iG if iG.node[n]['ClusterName'] ==
                    data['ClusterName']])
                writer.writerow([
                    data['ClusterName'], '/'.join(nodes), 'infomap'])
                visited.add(data['infomap'])
        for node, data in sG.nodes(data=True):
            if data['ClusterName'] not in visited:
                nodes = sorted(data['subgraph'])
                writer.writerow([
                    data['ClusterName'], '/'.join(nodes), 'subgraph'])
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



