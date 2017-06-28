from pyclics.utils import *
from glob import glob
import os
from clldutils.dsv import UnicodeReader
import networkx as nx
from itertools import combinations
import pickle
import lingpy
from lingpy.convert.graph import networkx2igraph
import igraph
from pyclics.providers import *
from pyglottolog.api import Glottolog

ids_list = Concepticon().conceptlists['List-2014-1280']
glottolog = Glottolog()
concepticon = load_concepticon()
clics_files = glob(clics_path('cldf', '*.csv'))

def check(word):
    if ',' in str(word): return '"'+str(word)+'"'
    return str(word)

def get_languages(verbose=False):
    concepts = defaultdict(list)
    data = {}
    out = 'Identifier,Language_name,Language_ID,Family,Longitude,Latitude\n'
    md = "# Languages in CLICS\n\nNumber | Language | Family | Size | Source\n--- | --- | --- | --- | --- \n"
    count, nan = 1, 1
    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['family'] == '':
            wl['meta']['family'] = 'NAN-{0}'.format(nan)
            nan += 1
            write_clics_wordlist(wl, clics_path('cldf',
                wl['meta']['identifier']+'.csv'))
        if wl['meta']['longitude']:
            out += '{0},{1},{2},{3},{4},{5}\n'.format(
                    wl['meta']['identifier'],
                    wl['meta']['name'],
                    wl['meta']['glottocode'],
                    wl['meta']['family'],
                    wl['meta']['longitude'],
                    wl['meta']['latitude'])
            wl['meta']['size'] = len(wl['identifiers'])
            data[wl['meta']['identifier']] = wl['meta']

            # add markdown
            md += '{0} | [{1}](http://glottolog.org/resource/languoid/id/{2}) | {3} | {4} | {5} \n'.format(
                    count,
                    wl['meta']['name'],
                    wl['meta']['glottocode'],
                    wl['meta']['family'],
                    wl['meta']['size'],
                    wl['meta']['source'])
            count += 1
    geos = make_language_map(data)
    with open(clics_path('geo', 'languages.geojson'), 'w') as f:
        json.dump(geos, f)
    with open(clics_path('stats', 'languages.csv'), 'w') as f:
        f.write(out)
    with open(clics_path('cldf', 'README.md'), 'w') as f:
        f.write(md)

def get_articulationpoints(graphname='network', edgefilter='families',
        verbose=False, normalize=True, threshold=1, subgraph='infomap'):
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
    threshod : int (default=1)
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

    graph = pickle.load(
            open(
                clics_path(
                    'graphs', 
                    '{0}-{1}-{2}.bin'.format(
                        graphname, threshold,  edgefilter
                        )
                    ), 'rb'))
    coms = defaultdict(list)
    for node, data in graph.nodes(data=True):
        coms[data['infomap']] += [node]
    _tmp = []
    for com, nodes in sorted(coms.items(), key=lambda x: len(x),
            reverse=True):
        if len(nodes) > 5:
            subgraph = graph.subgraph(nodes)
            degrees = subgraph.degree(list(subgraph.nodes()))
            cnodes = sorted(degrees, key=lambda x: degrees[x],
                    reverse=True)
            cnode = cnodes[0]
            graph.node[cnode]['DegreeCentrality'] = 1
            artipoints = nx.articulation_points(subgraph)
            for artip in artipoints:
                if 'ArticulationPoint' in graph.node[artip]:
                    graph.node[artip]['ArticulationPoint'] += 1
                else:
                    graph.node[artip]['ArticulationPoint'] = 1
                if verbose: print('{0}\t{1}\t{2}'.format(
                    com, graph.node[cnode]['Gloss'], 
                    graph.node[artip]['Gloss']))
                _tmp += [(artip, graph.node[artip]['Gloss'], 
                    com, cnode, graph.node[cnode]['Gloss'], len(nodes))]
            if verbose: print('')
    for node, data in graph.nodes(data=True):
        if not 'ArticulationPoint' in data:
            data['ArticulationPoint'] = 0
        if not 'DegreeCentrality' in data:
            data['DegreeCentrality'] = 0

    out = 'ConcepticonId,ConcepticonGloss,Community,CommunitySize,CentralNode,CentralNodeGloss\n'
    md = '# Articulation Points (Analysis {0} / {1})\n\n'.format(threshold,
            edgefilter)
    md += 'Number | Concept | Community | CommunitySize | CentralNode \n'
    md += '--- | --- | --- | --- | --- \n'
    for i, line in enumerate(_tmp):
        out += ','.join([check(w) for w in line])+'\n'
        md += '{1} | [{0[1]}]({0[0]}) | {0[2]} | {0[5]} | [{0[4]}]({0[3]}) \n'.format(
                line, i+1)
    
    with open(clics_path('stats',
        'articulationpoints-{0}-{1}.csv'.format(threshold, edgefilter)), 'w') as f:
        f.write(out)
    with open(clics_path('stats',
        'articulationpoints-{0}-{1}.md'.format(threshold, edgefilter)), 'w') as f:
        f.write(md)
    save_network(clics_path('graphs', 'articulationpoints-{0}-{1}.gml'.format(
        threshold,
        edgefilter
        )), graph)


def get_cocitation_graph(graphname='dinetwork', threshold=3,
        edgefilter='families', verbose=True, weight='FamilyWeight'):
    graph = load_network(clics_path('graphs', '{0}-{1}-{2}.gml'.format(
        graphname, threshold, edgefilter)))
    igr = networkx2igraph(graph)
    v = igr.bibcoupling()
    return v, igr, graph


def get_transitions(graphname='network', threshold=3, edgefilter='family',
        verbose=True, aspect='semanticfield', weight='FamilyWeight',
        assymetric=True):
    graph = pickle.load(open(clics_path('graphs', '{0}-{1}-{2}.bin'.format(
        graphname, threshold, edgefilter)), 'rb'))

    trs = defaultdict(list)
    for nA, nB, data in graph.edges(data=True):
        catA = concepticon[nA].get(aspect, '?')
        catB = concepticon[nB].get(aspect, '?')
        trs[catA, catB] += [(nA, nB, data[weight])]
    
    out = '# Transitions (Analysis t={0}, f={1})\n'.format(threshold,
            edgefilter)
    for (catA, catB),values in sorted(trs.items(), key=lambda x: len(x[1]),
            reverse=True):

        if len(values) > 2:
            if (assymetric and catA != catB) or not assymetric:
                if verbose: print('{0:40} -> {1:40} / {2}'.format(catA, catB,
                    len(values))) 
                out += '## {0} -> {1} / {2}\n'.format(catA, catB, len(values))
                for a, b, c in values:
                    out += '{0:20} -> {1:20} / {2}\n'.format(
                            concepticon[a]['GLOSS'], concepticon[b]['GLOSS'],
                            c)
                out += '\n'
    with open(clics_path('stats', 'transitions-{0}-{1}.md'.format(threshold,
        edgefilter)), 'w') as f:
        f.write(out)


def get_communities(graphname='network', edge_weights='FamilyWeight',
        vertex_weights='FamilyFrequency', verbose=False, normalize=True,
        edgefilter='families', threshold=1):

    _graph = pickle.load(
            open(
                clics_path(
                    'graphs', 
                    '{0}-{1}-{2}.bin'.format(
                        graphname, threshold,  edgefilter
                        )
                    ), 'rb'))
    for n, d in _graph.nodes(data=True):
        d[vertex_weights] = int(d[vertex_weights])
    
    if normalize:
        for edgeA, edgeB, data in _graph.edges(data=True):
            data['weight'] = data[edge_weights] ** 2 / (
                    _graph.node[edgeA][vertex_weights] + \
                            _graph.node[edgeB][vertex_weights] - \
                            data[edge_weights])
        vertex_weights=None
        edge_weights='weight'
        if verbose: print('[i] computed weights')

    graph = networkx2igraph(_graph)
    if verbose: print('[i] converted graph...')
    comps = graph.community_infomap(edge_weights=edge_weights,
            vertex_weights=vertex_weights)
    D = {}
    out = ''
    for i, comp in enumerate(comps.subgraphs()):
        vertices = [v['name'] for v in comp.vs]
        for vertex in vertices:
            if verbose: print(graph.vs[vertex]['Gloss'], i+1)
            D[graph.vs[vertex]['ConcepticonId']] = i+1
            out += '{0},{1},{2}\n'.format(graph.vs[vertex]['ConcepticonId'], graph.vs[vertex]['Gloss'],
                    i+1)
        if verbose: print('---')
    for node, data in _graph.nodes(data=True):
        data['infomap'] = D[node]

    with open(clics_path('communities', 'infomap.csv'), 'w') as f:
        f.write(out)
    save_network(clics_path('graphs', 'infomap-{0}-{1}.gml'.format(
        threshold,
        edgefilter
        )), _graph)
    with open(clics_path('graphs', 'infomap-{0}-{1}.bin'.format(
        threshold,
        edgefilter)), 'wb') as f:
        pickle.dump(_graph, f)


def get_coverage(verbose=False):
    concepts = defaultdict(list)
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]
    
    out1 = 'WordID,ConcepticonId,ConcepticonGloss,Gloss,LanguageId,LanguageName,Family,Value,ClicsValue\n'
    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            cidx, vidx, oidx, gidx = (wl[0].index('Parameter_ID'),
                    wl[0].index('Clics_Value'), wl[0].index('Value'),
                    wl[0].index('Parameter_name'))
            for idx in wl['identifiers']:
                concept = wl[idx][cidx]
                value = wl[idx][vidx]

                if concept and concepticon[concept].get('gloss', ''):
                    concepts[concept] += [(wl['meta']['family'],
                        wl['meta']['identifier'], idx)]
                    out1 += ','.join([check(w) for w in [
                        idx, concept, concepticon[concept]['gloss'], wl[idx][gidx], wl['meta']['glottocode'],
                        wl['meta']['name'], wl['meta']['family'], wl[idx][oidx],
                        value]]) + '\n'

    out2 = 'ID,Gloss,Semanticfield,Category,WordFrequency,LanguageFrequency,FamilyFrequency,Words,Languages,Families\n'
    md = '# Concepts in CLICS\n'
    md += 'Number | Concept | SemanticField | Category | Reflexes \n --- | --- | --- | --- |--- \n'
    for i, (concept, lists) in enumerate(concepts.items()):
        out2 += '{0},{1},{2},{3},{4},{5},{6},"{7}","{8}","{9}"\n'.format(
                concept, concepticon[concept]['gloss'],
                concepticon[concept]['semanticfield'],
                concepticon[concept]['ontological_category'],
                len(set([x[0] for x in lists])),
                len(set([x[1] for x in lists])),
                len(lists),
                ';'.join(sorted(set([x[2] for x in lists]))),
                ';'.join(sorted(set([x[1] for x in lists]))),
                ';'.join(sorted(set([x[0] for x in lists])))
                )
        md += '{0} | [{1}](http://concepticon.clld.org/parameters/{2}) | {3} | {4} | {5} \n'.format(
                i+1, concepticon[concept]['gloss'], concept, 
                concepticon[concept]['semanticfield'],
                concepticon[concept]['ontological_category'],
                len(lists))
    with open(clics_path('stats', 'concepts.csv'), 'w') as f:
        f.write(out2)
    with open(clics_path('data', 'words.csv'), 'w') as f:
        f.write(out1)
    with open(clics_path('stats', 'concepts.md'), 'w') as f:
        f.write(md)

    return concepts


def get_colexification_dump(verbose=False):
    colexifications = {}
    with UnicodeReader(clics_path('stats', 'concepts.csv')) as reader:
        _tmp = list(reader)
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]
    with UnicodeReader(clics_path('stats', 'colexifications.csv')) as reader:
        all_colexifications = [(line[0],line[1]) for line in reader][1:]
    concepts = set()
    for c1, c2 in all_colexifications:
        concepts.add(c1)
        concepts.add(c2)
    concepts = sorted(concepts)

    mydump = open(clics_path('dumps', 'dump.csv'), 'w')

    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            cols = full_colexification(wl, key='Parameter_ID', entry='Clics_Value',
                    indices='identifiers')
            tmp = defaultdict(int)
            for k, v in cols.items():
                for (conceptA, idxA), (conceptB, idxB) in combinations(v, r=2):
                    tmp[conceptA, conceptB] += 1
                    tmp[conceptB, conceptA] += 1
                for cnc, idx in v:
                    tmp[cnc, cnc] += 1
            for cnc in concepts:
                mydump.write(','.join([
                    wl['meta']['family'], wl['meta']['identifier'],
                    '"'+concepticon[cnc]['gloss']+'"',
                    '"'+concepticon[cnc]['gloss']+'"',
                    str(tmp[cnc,
                        cnc])])+'\n')
            for cidxA, cidxB in all_colexifications:
                if tmp[cidxA, cidxB] or (tmp[cidxA, cidxA] and tmp[cidxB,
                    cidxB]):
                    mydump.write(','.join([
                        wl['meta']['family'], 
                        wl['meta']['identifier'],
                        '"'+concepticon[cidxA]['gloss']+'"',
                        '"'+concepticon[cidxB]['gloss']+'"', str(tmp[cidxA,
                            cidxB])])+'\n')
                elif not tmp[cidxA, cidxA] or not tmp[cidxB, cidxB]:
                    mydump.write(','.join([
                        wl['meta']['family'], 
                        wl['meta']['identifier'],
                        '"'+concepticon[cidxA]['gloss']+'"',
                        '"'+concepticon[cidxB]['gloss']+'"', '-1'])+'\n')
    mydump.close()


def get_partialcolexification(cutoff=5, edgefilter='families', verbose=False,
        threshold=3, pairs='infomap.csv', graphname='infomap', 
        weight='FamilyWeight'):
    """Function computes partial colexification graph of a given pre-clustered \
            graph.

    Notes
    -----
    Essentially, the search space is restricted in this approach by two
    factors:

    1. only search within the same community for partial colexifications
    2. include the highest cross-community edges.
    
    """
    with UnicodeReader(clics_path('stats', 'concepts.csv')) as reader:
        _tmp = list(reader)
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]

    concepts = dict([(x[0], dict(zip(_tmp[0], x))) for x in _tmp[1:]])
    G = nx.DiGraph()
    for idx, vals in concepts.items():
        vals['ConcepticonId'] = vals['ID']
        G.add_node(idx, **vals)
    with UnicodeReader(clics_path('communities', pairs)) as reader:
        coms = defaultdict(list)
        for a, b, c in reader:
            coms[c] += [a]
            G.node[a]['community'] = c
    _graph = pickle.load(
            open(clics_path('graphs', '{0}-{1}-{2}.bin'.format(
                        graphname, threshold,  edgefilter)), 'rb'))
    cidx = 1
    for nA, nB, data in _graph.edges(data=True):
        if _graph.node[nA]['infomap'] != _graph.node[nB]['infomap']:
            if data[weight] >= threshold:
                coms[cidx] = [nA, nB]
                cidx += 1

    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        pcolnum = 0
        if wl['meta']['identifier'] in languages:
            for com, nodes in coms.items():
                pcols = partial_colexification(wl, nodes, key='Parameter_ID',
                        indices='identifiers', threshold=cutoff, 
                        entry='Clics_Value')
                pcolnum += len(pcols)
                for (idxA, wordA, conceptA, idxB, wordB, conceptB) in pcols:
                    if G.edge.get(conceptA, {}).get(conceptB, False):
                        G.edge[conceptA][conceptB]['words'].add((idxA, idxB))
                        G.edge[conceptA][conceptB]['languages'].add(wl['meta']['identifier'])
                        G.edge[conceptA][conceptB]['families'].add(wl['meta']['family'])
                    else:
                        G.add_edge(conceptA, conceptB, words=set([(idxA, idxB)]),
                                languages=set([wl['meta']['identifier']]),
                                families=set([wl['meta']['family']]))
    ignore_edges = []
    out = ''
    for edgeA, edgeB, data in G.edges(data=True):
        data['WordWeight'] = len(data['words'])
        data['words'] = ';'.join(sorted(['{0}/{1}'.format(x, y) for x, y in
            data['words']]))
        data['FamilyWeight'] = len(data['families'])
        data['families'] = ';'.join(sorted(data['families']))
        data['LanguageWeight'] = len(data['languages'])
        data['languages'] = ';'.join(data['languages'])
        if edgefilter == 'families' and data['FamilyWeight'] < threshold:
            ignore_edges += [(edgeA, edgeB)]
        elif edgefilter == 'languages' and data['LanguageWeight'] < threshold:
            ignore_edges += [(edgeA, edgeB)]
        elif edgefilter == 'words' and data['WordWeight'] < threshold:
            ignore_edges += [(edgeA, edgeB)]
        out += ','.join([str(x) for x in [
            edgeA, edgeB, data['FamilyWeight'], data['LanguageWeight'],
            data['WordWeight']]])+'\n'
    G.remove_edges_from(ignore_edges)

    save_network(clics_path('graphs', 'digraph-{0}-{1}.gml'.format(
        threshold,
        edgefilter
        )), G)
    with open(clics_path('stats', 'partialcolexifications-{0}-{1}.csv'.format(
        threshold,
        edgefilter)), 'w') as f:
        f.write(out)
    with open(clics_path('graphs', 'digraph-{0}-{1}.bin'.format(
        threshold,
        edgefilter)), 'wb') as f:
        pickle.dump(G, f)
            


def get_colexification_graph(threshold=5, edgefilter='families', verbose=False):
    colexifications = {}
    with UnicodeReader(clics_path('stats', 'concepts.csv')) as reader:
        _tmp = list(reader)
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]

    concepts = dict([(x[0], dict(zip(_tmp[0], x))) for x in _tmp[1:]])
    G = nx.Graph()
    for idx, vals in concepts.items():
        vals['ConcepticonId'] = vals['ID']
        G.add_node(idx, **vals)

    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            cols = full_colexification(wl, key='Parameter_ID', entry='Clics_Value',
                    indices='identifiers')
            for k, v in cols.items():
                for (conceptA, idxA), (conceptB, idxB) in combinations(v, r=2):
                    # check for identical concept resulting from word-variants
                    if conceptA != conceptB:
                        if G.edge.get(conceptA, {}).get(conceptB, False):
                            G.edge[conceptA][conceptB]['words'].add((idxA, idxB))
                            G.edge[conceptA][conceptB]['languages'].add(wl['meta']['identifier'])
                            G.edge[conceptA][conceptB]['families'].add(wl['meta']['family'])
                        else:
                            G.add_edge(conceptA, conceptB, words=set([(idxA, idxB)]),
                                    languages=set([wl['meta']['identifier']]),
                                    families=set([wl['meta']['family']]))
    ignore_edges = []
    out = 'EdgeA,EdgeB,FamilyWeight,LanguageWeight,WordWeight\n'
    for edgeA, edgeB, data in G.edges(data=True):
        data['WordWeight'] = len(data['words'])
        data['words'] = ';'.join(sorted(['{0}/{1}'.format(x, y) for x, y in
            data['words']]))
        data['FamilyWeight'] = len(data['families'])
        data['families'] = ';'.join(sorted(data['families']))
        data['LanguageWeight'] = len(data['languages'])
        data['languages'] = ';'.join(data['languages'])
        if edgefilter == 'families' and data['FamilyWeight'] < threshold:
            ignore_edges += [(edgeA, edgeB)]
        elif edgefilter == 'languages' and data['LanguageWeight'] < threshold:
            ignore_edges += [(edgeA, edgeB)]
        elif edgefilter == 'words' and data['WordWeight'] < threshold:
            ignore_edges += [(edgeA, edgeB)]
        out += ','.join([str(x) for x in [
            edgeA, edgeB, data['FamilyWeight'], data['LanguageWeight'],
            data['WordWeight']]])+'\n'

    G.remove_edges_from(ignore_edges)
    
    save_network(clics_path('graphs', 'network-{0}-{1}.gml'.format(
        threshold,
        edgefilter
        )), G)
    with open(clics_path('graphs', 'network-{0}-{1}.bin'.format(
        threshold,
        edgefilter)), 'wb') as f:
        pickle.dump(G, f)
    with open(clics_path('stats', 'colexifications-{0}-{1}.csv'.format(
        threshold,
        edgefilter)), 'w') as f:
        f.write(out)
    

def main():

    from sys import argv
    
    if '-h' in argv or '--help' in argv or 'help' in argv:
        print("Usage: clics [load|get] [ids|wold|nelex|colexification|coverage]")
    
    # basic parameters
    verbose, threshold, edgefilter, normalize, graphname, weight, aspect = (False, 1, 
            'families', False, 'network', 'FamilyWeight', 'WORDNET_FIELD')
    if '-v' in argv:
        verbose=True
    if '-t' in argv:
        threshold = int(argv[argv.index('-t')+1])
    if '-f' in argv:
        edgefilter = argv[argv.index('-f')+1]
    if '-n' in argv:
        normalize = True
    if '-g' in argv:
        graphname=argv[argv.index('-g')+1]
    if '-w' in argv:
        weight = argv[argv.index('-w')+1]
    if '-a' in argv:
        aspect = argv[argv.index('-a')+1]

    if 'load' in argv:
        if 'ids' in argv:
            load_ids(verbose=verbose)
        if 'wold' in argv:
            load_wold(verbose=verbose)
        if 'nelex' in argv:
            load_nelex(verbose=verbose)
        if 'baidial' in argv:
            load_baidial(verbose=verbose)
        if 'tryonhackman' in argv:
            load_tryon(verbose=verbose)
        if 'kraft' in argv:
            load_kraft(verbose=verbose)
        if 'huber' in argv:
            load_huber(verbose=verbose)

    if 'clean' in argv:
        os.system('rm '+str(clics_path('cldf', '*')))
    
    if 'get' in argv:

        if 'colexification' in argv:
            get_colexification_graph(threshold=threshold,
                    edgefilter=edgefilter, verbose=verbose)

        if 'coverage' in argv:
            get_coverage(verbose=verbose)

        if 'languages' in argv:
            get_languages(verbose=verbose)
        
        if 'dump' in argv:
            get_colexification_dump(verbose=verbose)

        if 'community' in argv:
            get_communities(verbose=verbose, normalize=normalize,
                    edgefilter=edgefilter,
                    threshold=threshold, graphname=graphname)

        if 'articulationpoint' in argv:
            get_articulationpoints(verbose=verbose, graphname=graphname,
                    threshold=threshold, edgefilter=edgefilter)

        if 'partialcolexification' in argv:
            get_partialcolexification(verbose=verbose, cutoff=3, weight=weight,
                    graphname=graphname, threshold=threshold)

        if 'transition' in argv:
            get_transitions(verbose=verbose, threshold=threshold,
                    edgefilter=edgefilter, weight=weight, graphname=graphname,
                    aspect=aspect)

