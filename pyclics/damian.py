from itertools import combinations
import lingpy

from pyconcepticon.api import Concepticon

from pyclics.api import Clics
from pyclics.utils import load_concepticon


def align_words(word1, word2):
    """
    Alternative: strip off the gaps to left and right!
    """
    almA, almB, sim = lingpy.nw_align(word1, word2)
    m, n = len(word1), len(word2)

    if m <= n:
        start, end = almA.index(word1[0]), len(almA)-almA[::-1].index(word1[-1])
    else:
        start, end = almB.index(word2[0]), len(almB)-almB[::-1].index(word2[-1])

    d = len([a for a, b in zip(almA, almB) if a != b])
    l = len([a for a, b in list(zip(almA, almB))[start:end] if a != b])
    return [m, n, d, l]


def special_colexification(wordlist,
                           concepticon,
                           key='Parameter_ID',
                           entry='Clics_Value',
                           indices='identifiers',
                           concepts=None,
                           concepticon_=None):
    if not concepts:
        concepts = [
            x.concepticon_id for x in
            concepticon_.conceptlists['List-2014-1280'].concepts.values()]

    key_idx = wordlist[0].index(key)
    entry_idx = wordlist[0].index(entry)
    subset = [i for i in wordlist[indices] if wordlist[i][key_idx] in concepts]
    for i, j in combinations(subset, r=2):
        w1, w2 = wordlist[i][entry_idx], wordlist[j][entry_idx]
        p1, p2 = wordlist[i][key_idx], wordlist[j][key_idx]
        four = align_words(w1, w2)
        yield [concepticon[p1]['gloss'], concepticon[p2]['gloss']] + four


def damian(clics, concepticon, glottolog_repos):
    snoek = [
        x.concepticon_id for x in
        concepticon.conceptlists['Snoek-2013-61'].concepts.values()] + \
            ['1301'] + ['1277'] + ['126']
    conc = load_concepticon(clics, concepticon)
    languages = [line[0] for line in clics.csv_reader('stats', 'languages')]
    with clics.csv_writer('dumps', 'damian', delimiter='\t', suffix='tsv') as writer:
        for i, wl in clics.enumerate_wordlists(glottolog_repos):
            if wl['meta']['identifier'] in languages:
                for line in special_colexification(
                        wl, conc, concepts=snoek, concepticon_=concepticon):
                    writer.writerow(
                        [
                            wl['meta']['name'],
                            wl['meta']['glottocode'],
                            wl['meta']['family']
                        ] + line)


if __name__ == '__main__':
    damian(
        Clics('.'),
        Concepticon('../../concepticon/concepticon-data'),
        '../../glottolog3/glottolog')
