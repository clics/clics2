# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict
from itertools import combinations
import geojson
import unidecode

from six import text_type
from clldutils.dsv import reader
from clldutils.misc import slug as _slug
from clldutils import jsonlib


def load_concepticon(clics_api, concepticon_api):
    concepticon = {cs.id: cs.__dict__ for cs in concepticon_api.conceptsets.values()}
    for a, b, c in clics_api.csv_reader('metadata', 'semantic_fields'):
        concepticon[a]['wordnet_field'] = b
        concepticon[a]['hypernym'] = c
    return concepticon


def slug(word):
    if not isinstance(word, text_type):
        word = word.decode('utf8')
    try:
        return _slug(word)
    except AssertionError:
        out = ''
        for x in word:
            try:
                out += _slug(x)
            except AssertionError:
                pass
        return out


def read_cldf_wordlist(
    lines,
    glottolog,
    source='',
    language_name='Language_name',
    glottocode='Language_ID',
    conceptset='Parameter_ID',
    conceptcolumn='Parameter_name',
    metadata=False,
    languoids=None,
):
    meta = None
    languoids = languoids or {}
    if not isinstance(lines, list):
        if metadata:
            meta = jsonlib.load(lines.parent.joinpath(lines.name + '-metadata.json'))
        lines = list(reader(lines))
    header = lines.pop(0)

    if not meta:
        name, gid = [lines[0][header.index(head)] for head in [language_name, glottocode]]
        languoid = languoids.get(gid) or glottolog.languoid(gid)
        if not languoid:
            return {}
        meta = dict(
            name=name,
            glottocode=gid,
            size=len(lines),
            source=source,
            classification=', '.join([a.name for a in languoid.ancestors]),
            macroarea=[a.name for a in languoid.macroareas],
            latitude=languoid.latitude,
            longitude=languoid.longitude,
            identifier='{0}_{1}_{2}'.format(slug(name), source, gid),
            family=languoid.family.name if languoid.family else ''
        )

    D = dict(identifiers=[])
    for i, line in enumerate(lines):
        idf, name, concept, cid, value = [
            line[header.index(head)]
            for head in ['ID', language_name, conceptcolumn, conceptset, 'Value']]
        latin_val = slug(unidecode.unidecode(value))
        if latin_val:
            D[idf] = [
                meta['identifier'],
                meta['glottocode'],
                name,
                concept,
                cid,
                value,
                latin_val,
                idf]
            D['identifiers'] += [idf]
    D[0] = [
        'Doculect_id',
        'Language_ID',
        'Language_name',
        'Parameter_name',
        'Parameter_ID',
        'Value',
        'Clics_Value',
        'Source_ID']
    D['meta'] = meta
    return D


def full_colexification(wordlist, key='ids_key', entry='entry', indices='indices'):
    """
    Calculate all colexifications inside a wordlist.

    :param wordlist: The wordlist storing the words, as produced by the
        read_cldf_wordlist function.
    :param str key: The name of the column storing the concepts in the
        header.
    :param str entry: The name of the column storing the actual words.
    :param str indices: The name of the key to the dictionary storing the
        indices.

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
    
    # get the key-index
    key_idx = wordlist[0].index(key)
    entry_idx = wordlist[0].index(entry)
    for idx in wordlist[indices]:
        word, concept = wordlist[idx][entry_idx], wordlist[idx][key_idx]
        if word and concept:
            cols[word] += [(concept, idx)]

    return cols


def partial_colexification(wordlist,
                           nodes,
                           key='Parameter_ID',
                           entry='Clics_Value',
                           indices='identifiers',
                           threshold=5):
    """Carry out a partial colexification analysis for a given wordlist.

    Parameters
    ----------
    wordlist : dict
        A wordlist object, as produced by the read_cldf_wordlist function.
    nodes : list
        Restrict the search for partial colexifications by passing a list of
        concepts to be searched.
    
    """
    pcols = []
    key_idx = wordlist[0].index(key)
    entry_idx = wordlist[0].index(entry)
    combis = []
    for idx in wordlist[indices]:
        concept = wordlist[idx][key_idx]
        if concept in nodes:
            combis += [idx]
    for idxA, idxB in combinations(combis, r=2):
        wordA, conceptA = wordlist[idxA][entry_idx], wordlist[idxA][key_idx]
        wordB, conceptB = wordlist[idxB][entry_idx], wordlist[idxB][key_idx]
        if conceptA != conceptB:
            sim = similar(wordA, wordB)
            if sim.endswith('1'):
                pcols += [(idxA, wordA, conceptA, idxB, wordB, conceptB)]
            elif sim.endswith('2'):
                pcols += [(idxB, wordB, conceptB, idxA, wordA, conceptA)]
    return pcols


def similar(word1, word2, min_len=5):
    """
    Determine similarity between words based on different principles.

    Note
    ----
    We check similarity by testing whether words are equal, whether one word is
    a prefix of another word, or vice verse.
    """
    if ' ' in word1:
        word1 = ''.join(word1.split(' '))
    if ' ' in word2:
        word2 = ''.join(word2.split(' '))

    if len(word1) < min_len or len(word2) < min_len:
        return ''

    if word1 == word2:
        return 'equal'
    if word1.startswith(word2):
        return 'prefix2'
    if word1.endswith(word2):
        return 'suffix2'
    if word2.startswith(word1):
        return 'prefix1'
    if word2.endswith(word1):
        return 'suffix1'

    return ''


def prefix_colexification(wordlist,
                          key='Feature_ID',
                          entry='IPA_UDECODE',
                          indices='indices',
                          min_len=5,
                          restrict=False):
    """
    Compute full colexifications.
    """
    cols = defaultdict(list)
    key_idx = wordlist[0].index(key)
    entry_idx = wordlist[0].index(entry)
    for idxA, idxB in combinations(wordlist[indices], r=2):
        conceptA, conceptB = wordlist[idxA][key_idx], wordlist[idxB][key_idx]
        if not restrict or (
                (conceptA, conceptB) in restrict or (conceptB, conceptA) in restrict):
            # word1 is prefix or suffix in word2
            wordA, wordB = wordlist[idxA][entry_idx], wordlist[idxB][entry_idx]
            sim = similar(wordA, wordB, min_len)
            if sim and sim != 'equal':
                if sim[-1] == '2':
                    cols[conceptB, conceptA].append((idxB, idxA))
                else:
                    cols[conceptA, conceptB].append((idxA, idxB))
    return cols


def make_language_map(data):
    """
    Create geojson map of the data, with additional information.
    """
    def _feature(meta):
        if meta['size'] < 800:
            marker_color = '#00ff00'
        elif meta['size'] < 1200:
            marker_color = '#ff00ff'
        else:
            marker_color = '#0000ff'
        return geojson.Feature(
            geometry=geojson.Point((meta['longitude'], meta['latitude'])),
            properties={
                "language": meta['name'],
                "coverage": meta['size'],
                "family": meta['family'],
                "area": meta['macroarea'],
                "marker-size": 'small',
                "marker-color": marker_color})

    return geojson.FeatureCollection([_feature(m) for m in data.values()])
