from pyclics.utils import *
from glob import glob
import os
from clldutils.dsv import UnicodeReader
import networkx as nx
from itertools import combinations
import pickle

ids_list = Concepticon().conceptlist('List-2014-1280')
glottolog = load_glottolog()
concepticon = load_concepticon()
clics_files = glob(clics_path('cldf', '*.csv'))


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
    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
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
    geos = make_language_map(data)
    with open(clics_path('geo', 'languages.geojson'), 'w') as f:
        json.dump(geos, f)
    with open(clics_path('stats', 'languages.csv'), 'w') as f:
        f.write(out)


def get_coverage(verbose=False):
    concepts = defaultdict(list)
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]

    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            cidx, vidx = wl[0].index('Parameter_ID'), wl[0].index('Clics_Value')
            for idx in wl['identifiers']:
                concept = wl[idx][cidx]
                value = wl[idx][vidx]
                concepts[concept] += [(wl['meta']['family'],
                    wl['meta']['identifier'], idx)]
    out = 'ID,Gloss,Semanticfield,Category,WordFrequency,LanguageFrequency,FamilyFrequency,Words,Languages,Families\n'
    for i, (concept, lists) in enumerate(concepts.items()):
        out += '{0},{1},{2},{3},{4},{5},{6},"{7}","{8}","{9}"\n'.format(
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
    with open(clics_path('stats/concepts.csv'), 'w') as f:
        f.write(out)
    return concepts

def get_colexification_graph(threshold=5, edgefilter='families', verbose=False):
    colexifications = {}
    with UnicodeReader(clics_path('stats', 'concepts.csv')) as reader:
        _tmp = list(reader)
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]

    concepts = dict([(x[0], dict(zip(_tmp[0], x))) for x in _tmp[1:]])
    G = nx.Graph()
    for idx, vals in concepts.items():
        G.add_node(idx, **vals)

    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            cols = full_colexification(wl, key='Parameter_ID', entry='Clics_Value',
                    indices='identifiers')
            for k, v in cols.items():
                for (conceptA, idxA), (conceptB, idxB) in combinations(v, r=2):
                    if G.edge.get(conceptA, {}).get(conceptB, False):
                        G.edge[conceptA][conceptB]['words'].add((idxA, idxB))
                        G.edge[conceptA][conceptB]['languages'].add(wl['meta']['identifier'])
                        G.edge[conceptA][conceptB]['families'].add(wl['meta']['family'])
                    else:
                        G.add_edge(conceptA, conceptB, words=set([(idxA, idxB)]),
                                languages=set([wl['meta']['identifier']]),
                                families=set([wl['meta']['family']]))
    ignore_edges = []
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
    G.remove_edges_from(ignore_edges)
    
    save_network(clics_path('graphs', 'network.gml'), G)
    with open(clics_path('graphs', 'network.bin'), 'wb') as f:
        pickle.dump(G, f)
    

if __name__ == '__main__':

    from sys import argv
    verbose,threshold,edgefilter=False, 5, 'families'
    if '-v' in argv:
        verbose=True
    if '-t' in argv:
        threshold = argv[argv.index('-t')+1]
    if '-f' in argv:
        edgefilter = argv[argv.index('-f')+1]

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

