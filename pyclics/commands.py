from pyclics.utils import *
from glob import glob
import os
from clldutils.dsv import UnicodeReader
import networkx as nx
from itertools import combinations
import pickle
import lingpy
from lingpy.convert.graph import networkx2igraph

ids_list = Concepticon().conceptlist('List-2014-1280')
glottolog = load_glottolog()
concepticon = load_concepticon()
clics_files = glob(clics_path('cldf', '*.csv'))

def check(word):
    if ',' in str(word): return '"'+str(word)+'"'
    return str(word)



def load_ids(verbose=False):
    files = glob(lexibank_path('ids', 'cldf', '*.csv'))
    for i, f in enumerate([x for x in files if 'cognates.csv' not in x]):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=False,
                conceptcolumn='Concept',
                source='IDS')
        write_clics_wordlist(wl, clics_path('cldf',
            wl['meta']['identifier']+'.csv'))

def load_wold(verbose=False):
    files = glob(lexibank_path('wold', 'cldf', '*.csv'))
    for i, f in enumerate([x for x in files if 'cognates.csv' not in x]):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=False,
                conceptcolumn='Parameter_name',
                source='WOLD')
        write_clics_wordlist(wl, clics_path('cldf',
            wl['meta']['identifier']+'.csv'))

def get_languages(verbose=False):
    concepts = defaultdict(list)
    data = {}
    out = 'Identifier,Language_name,Language_ID,Family,Longitude,Latitude\n'
    md = "# Languages in CLICS\n\nNumber | Language | Family | Size | Source\n--- | --- | --- | --- | --- \n"
    count, nan = 1, 1
    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['family'] == 'NAN':
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
    for com, nodes in sorted(coms.items(), key=lambda x: len(x[1])):
        if len(nodes) > 5:
            subgraph = graph.subgraph(nodes)
            degrees = subgraph.degree(list(subgraph.nodes()))
            cnode = sorted(degrees, key=lambda x: x[1],
                    reverse=True)[0][0]
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
                    com, cnode, graph.node[cnode]['Gloss'])]
            if verbose: print('')
    for node, data in graph.nodes(data=True):
        if not 'ArticulationPoint' in data:
            data['ArticulationPoint'] = 0
        if not 'DegreeCentrality' in data:
            data['DegreeCentrality'] = 0

    out = 'ConcepticonId,ConcepticonGloss,Community,CentralNode,CentralNodeGloss\n'
    md = '# Articulation Points (Analysis {0} / {1})\n\n'.format(threshold,
            edgefilter)
    md += 'Concept | Community | CentralNode \n --- | --- | --- \n'
    for line in _tmp:
        out += ','.join([check(w) for w in line])+'\n'
        md += '[{0[1]}]({0[0]}) | {0[2]} | [{0[4]}]({0[3]}) \n'.format(line)
    
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
                concepts[concept] += [(wl['meta']['family'],
                    wl['meta']['identifier'], idx)]
                out1 += ','.join([check(w) for w in [
                    idx, concept, concepticon[concept]['GLOSS'], wl[idx][gidx], wl['meta']['glottocode'],
                    wl['meta']['name'], wl['meta']['family'], wl[idx][oidx],
                    value]]) + '\n'

    out2 = 'ID,Gloss,Semanticfield,Category,WordFrequency,LanguageFrequency,FamilyFrequency,Words,Languages,Families\n'
    md = '# Concepts in CLICS\n'
    md += 'Number | Concept | SemanticField | Category | Reflexes \n --- | --- | --- | --- |--- \n'
    for i, (concept, lists) in enumerate(concepts.items()):
        out2 += '{0},{1},{2},{3},{4},{5},{6},"{7}","{8}","{9}"\n'.format(
                concept, concepticon[concept]['GLOSS'],
                concepticon[concept]['SEMANTICFIELD'],
                concepticon[concept]['ONTOLOGICAL_CATEGORY'],
                len(set([x[0] for x in lists])),
                len(set([x[1] for x in lists])),
                len(lists),
                ';'.join(sorted(set([x[2] for x in lists]))),
                ';'.join(sorted(set([x[1] for x in lists]))),
                ';'.join(sorted(set([x[0] for x in lists])))
                )
        md += '{0} | [{1}](http://concepticon.clld.org/parameters/{2}) | {3} | {4} | {5} \n'.format(
                i+1, concepticon[concept]['GLOSS'], concept, 
                concepticon[concept]['SEMANTICFIELD'],
                concepticon[concept]['ONTOLOGICAL_CATEGORY'],
                len(lists))
    with open(clics_path('stats/concepts.csv'), 'w') as f:
        f.write(out2)
    with open(clics_path('data/words.csv'), 'w') as f:
        f.write(out1)
    with open(clics_path('stats/concepts.md'), 'w') as f:
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
    concepts = dict([(x[0], dict(zip(_tmp[0], x))) for x in _tmp[1:]])

    mydump = open(clics_path('dumps', 'dump.csv'), 'w')

    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            cols = full_colexification(wl, key='Parameter_ID', entry='Clics_Value',
                    indices='identifiers')
            tmp = set()
            for k, v in cols.items():
                for (conceptA, idxA), (conceptB, idxB) in combinations(v, r=2):
                    if conceptA != conceptB:
                        tmp.add((conceptA, conceptB))
                        tmp.add((conceptB, conceptA))
                mydump.write(','.join([
                    wl['meta']['family'], wl['meta']['identifier'],
                    concepticon[v[0][0]]['GLOSS'],
                    concepticon[v[0][0]]['GLOSS'], '1'])+'\n')
            for cidxA, cidxB in all_colexifications:
                if (cidxA, cidxB) in tmp:
                    mydump.write(','.join([
                        wl['meta']['family'], 
                        wl['meta']['identifier'],
                        concepticon[cidxA]['GLOSS'],
                        concepticon[cidxB]['GLOSS'], '1'])+'\n')
                else:
                    mydump.write(','.join([
                        wl['meta']['family'], 
                        wl['meta']['identifier'],
                        concepticon[cidxA]['GLOSS'],
                        concepticon[cidxB]['GLOSS'], '-1'])+'\n')
    mydump.close()

def get_partialcolexification(cutoff=5, edgefilter='families', verbose=False,
        threshold=3, pairs='infomap.csv'):
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
            print(a, c)
            G.node[a]['community'] = c


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

    save_network(clics_path('graphs', 'dinetwork-{0}-{1}.gml'.format(
        threshold,
        edgefilter
        )), G)
    with open(clics_path('stats', 'partialcolexifications-{0}-{1}.csv'.format(
        threshold,
        edgefilter)), 'w') as f:
        f.write(out)

            


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
        print("Usage: clics [load|get] [ids|wold|colexification|coverage]")
    
    # basic parameters
    verbose, threshold, edgefilter, normalize, graphname = False, 1, 'families', False, 'network'
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

    if 'load' in argv:
        if 'ids' in argv:
            load_ids(verbose=verbose)
        if 'wold' in argv:
            load_wold(verbose=verbose)
    
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
            get_partialcolexification(verbose=verbose, cutoff=5)

