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

ids_list = Concepticon().conceptlists['List-2014-1280']
body_parts = Concepticon().conceptlists['Snoek-2013-61']
glottolog = load_glottolog()
concepticon = load_concepticon()
clics_files = glob(clics_path('cldf', '*.csv'))

def align_words(word1, word2, verbose=False):
    """
    Alternative: strip off the gaps to left and right!
    """
    almA, almB, sim = lingpy.nw_align(word1, word2)
    m, n = len(word1), len(word2)
    d = 0
    ld = 0

    if m <= n:
        start, end = almA.index(word1[0]), len(almA)-almA[::-1].index(word1[-1])
    else:
        start, end = almB.index(word2[0]), len(almB)-almB[::-1].index(word2[-1])


    d = len([a for a, b in zip(almA, almB) if a != b])
    l = len([a for a, b in list(zip(almA, almB))[start:end] if a != b])
    if verbose:
        print(' '.join(almA))
        print(' '.join(almB))
        print(' '.join(almA[start:end]),start, end)
        print(' '.join(almB[start:end]),start, end)
    return [m, n, d, l]

def special_colexification(wordlist, key='Parameter_ID', entry='Clics_Value', 
        indices='identifiers', concepts=[]):
    if not concepts:
        concepts = [x.concepticon_id for x in ids_list.concepts.values()]

    key_idx = wordlist[0].index(key)
    entry_idx = wordlist[0].index(entry)
    subset = [i for i in wordlist[indices] if wordlist[i][key_idx] in concepts]
    for i, j in combinations(subset, r=2):
        w1, w2 = wordlist[i][entry_idx], wordlist[j][entry_idx]
        p1, p2 = wordlist[i][key_idx], wordlist[j][key_idx]
        four = align_words(w1, w2)
        yield [concepticon[p1]['gloss'], concepticon[p2]['gloss']] + four

def get_damian(verbose=False):
    snoek = [x.concepticon_id for x in
            body_parts.concepts.values()]+['1301']+['1277']+['126']
    with UnicodeReader(clics_path('stats', 'languages.csv')) as reader:
        languages = [line[0] for line in reader]
    file_ = open(clics_path('dumps', 'damian.csv'), 'w')
    for i, f in enumerate(clics_files):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=True)
        if wl['meta']['identifier'] in languages:
            for line in special_colexification(wl, concepts=snoek):
                file_.write('\t'.join([str(x) for x in [
                    wl['meta']['name'], wl['meta']['glottocode'],
                    wl['meta']['family']] + line])+'\n')
    file_.close()

if __name__ == '__main__':
    print('start')
    get_damian(verbose=True)
