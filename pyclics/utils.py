from collections import defaultdict
import json
from itertools import combinations
import geojson
from clldutils.dsv import UnicodeReader
import os
from functools import partial
import lingpy
import unidecode
import pylexibank as lexibank
from pyconcepticon.api import Concepticon
from collections import OrderedDict
from clldutils.misc import slug as _slug
import codecs
import html
import networkx as nx
import pickle
import os
from pyglottolog.api import Glottolog


def save_network(filename, graph, dump=False):
    if dump:
        with open(filename[:-3]+'bin', 'wb') as f:
            pickle.dump(graph, f)
    with codecs.open(filename, 'w', 'utf-8') as f:
        for line in nx.generate_gml(graph):
            f.write(html.unescape(line)+'\n')


def load_network(filename):
    if os.path.isfile(filename[:-3]+'bin'):
        return pickle.load(open(filename[:-3]+'bin', 'rb'))
    with codecs.open(filename, 'r', 'utf-8') as f:
        lines = [l.encode('ascii', 'xmlcharrefreplace').decode('utf-8') for l in f]
        return nx.parse_gml('\n'.join(lines))


def load_concepticon():

    concepticon = dict([
        (line.id, line.__dict__) for line in Concepticon().conceptsets.values()
        ])
    with UnicodeReader(clics_path('metadata', 'semantic_fields.csv')) as reader:
        for a, b, c in reader:
            concepticon[a]['wordnet_field'] = b
            concepticon[a]['hypernym'] = c
    return concepticon


def slug(word):
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


def clics_path(*comps):
    """
    Our data-path in CLICS.
    """
    return os.path.join(os.path.dirname(__file__), os.pardir, *comps)


def lexibank_path(*comps):
    """
    Path to lexibank-data, allows to assemble other datasets.
    """
    return os.path.join(os.path.dirname(lexibank.__file__), os.pardir, 'datasets', *comps)

"""
clics-data, as a shortcut function
"""
data_path = partial(clics_path, os.pardir, 'clics-data')


def load_glottolog():
    """
    Currently, we store glottolog as json, as it otherwise fails to load.

    Function deprecated now!
    """
    #G = json.load(open(clics_path('glottolog', 'glottolog.json')))

    #return G
    try: 
        G = json.load(open(clics_path('glottolog', 'glottolog.json')))
    except:
        glot = Glottolog()
        G = {}
        for lang in glot.languoids():
            G[lang.glottocode] = dict(
                    name = lang.name,
                    longitude = lang.longitude, 
                    latitude = lang.latitude,
                    family = getattr(lang.family, 'name') if lang.family else '',
                    family_code = getattr(lang.family, 'glottocode') if lang.family else '',
                    macroareas = [area.name for area in lang.macroareas],
                    ancestors = ", ".join([family.name for family in
                        lang.ancestors])
                    )
        with open(clics_path('glottolog', 'glottolog.json'), 'w') as f:
            json.dump(G, f)
    return G

def load_metadata():
    """
    Loading metadata from cldf-files.
    """
    G = json.load(open('clics-cldf-meta.json'))

    return G

def read_cldf_wordlist(path_or_lines, glottolog=False, source='', 
        language_name='Language_name', glottocode='Language_ID',
        conceptset='Parameter_ID', conceptcolumn='Parameter_name',
        metadata=True
        ):
    
    glottolog = glottolog or load_glottolog()
    if isinstance(path_or_lines, list):
        header = path_or_lines[0]
        lines = path_or_lines[1:]
        meta = metadata
    else:
        with UnicodeReader(path_or_lines) as reader:
            data = list(reader)
        header = data[0]
        lines = data[1:]
    
    if not metadata:
        name, gid = [lines[0][header.index(head)] for head in [language_name, glottocode]]
        languoid = glottolog.languoid(gid)
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
    else:
        meta = json.load(open(path_or_lines+'-metadata.json'))

    D = dict(identifiers = [])
    for i, line in enumerate(lines):
        idf, name, concept, cid, value = [line[header.index(head)] for head in
            ['ID', language_name, conceptcolumn, conceptset, 'Value']]
        latin_val = slug(unidecode.unidecode(value))
        if latin_val:
            D[idf] = [meta['identifier'], meta['glottocode'], name, concept, cid, value,
                    latin_val, idf]
            D['identifiers'] += [idf]
    D[0] = ['Doculect_id', 'Language_ID', 'Language_name', 'Parameter_name',
            'Parameter_ID', 'Value', 'Clics_Value', 'Source_ID']
    D['meta'] = meta
    return D

def write_clics_wordlist(wordlist, path):
    """
    Write wordlist in convenient clics format (basically cldf style, but with some additional columns.
    """
    def check(word):
        if ',' in word:
            return '"'+word+'"'
        return word

    header = wordlist[0]
    out = ''
    out += 'ID,'+','.join(header)+'\n'
    for idf in wordlist['identifiers']:
        out += check(idf)+','+','.join([check(word) for word in wordlist[idf]])+'\n'
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(out)
    json.dump(wordlist['meta'], open(path+'-metadata.json', 'w'))

def _read_cldf_concept_list(path, metadata=False):
    """
    retired function
    """
    meta = dict(
            classification = '',
            ids_name = '',
            iso = '',
            language = '',
            size = '',
            source = '',
            variety = ''
            )
    D = {}
    with open(path) as f:
        header = f.readline().strip().split(',')
        D[0] = [h for h in header if h != 'ID']
        D['indices'] = []
        for line in csv.reader(f):
            tmp = dict(zip(header, line))
            D[tmp['ID']] = [tmp[h] for h in D[0]]
            D['indices'] += [tmp['ID']]

    if metadata:
        lid = path.split('/')[-1][:-4]
        for k in metadata[lid]:
            D[k] = metadata[lid][k]

    return D

def read_clics_concept_list(path, glottolog=False):
    
    meta = dict(
            classification = '',
            ids_name = '',
            iso = '',
            language = '',
            size = '',
            source = '',
            variety = ''
            )
    meta[0] = ['ids_key', 'gloss', 'entry']
    meta['indices'] = []
    with open(path) as f:
        idx = 1
        for line in f:
            if line.startswith('@'):
                key, value = line[1:-1].split(':')
                meta[key.strip()] = value.strip()
            else:
                meta[idx] = [x.strip() for x in line.split('\t')]
                meta['indices'] += [idx]
                idx += 1
    
    if glottolog:
        glotto_code = glottolog['iso_'+meta['iso']]
        meta['glottolog'] = glotto_code
        for k in ['coordinates', 'population_numeric', 'classification-gl',
                'macroarea-gl']:
            try:
                meta[k] = glottolog[glotto_code][k]
            except KeyError:
                meta[k] = ''

    return meta

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
        cols[word] += [(concept, idx)]

    return cols

def partial_colexification(wordlist, nodes, key='Parameter_ID', entry='Clics_Value',
        indices='identifiers', threshold=5):
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

def prefix_colexification(wordlist, key='Feature_ID', entry='IPA_UDECODE', 
        indices='indices', min_len=5, restrict=False):
    """
    Compute full colexifications.
    """
    

    cols = {}
    key_idx = wordlist[0].index(key)
    entry_idx  = wordlist[0].index(entry)
    for idxA, idxB in combinations(wordlist[indices], r=2):
        conceptA, conceptB = wordlist[idxA][key_idx], wordlist[idxB][key_idx]
        if not restrict or ((conceptA, conceptB) in restrict or (conceptB,
                conceptA) in restrict):

            # word1 is prefix or suffix in word2
            wordA, wordB = wordlist[idxA][entry_idx], wordlist[idxB][entry_idx]
            sim = similar(wordA, wordB, min_len)
            if sim and sim != 'equal':
                if sim[-1] == '2':
                    try:
                        cols[conceptB, conceptA] += [(idxB, idxA)]
                    except KeyError:
                        cols[conceptB, conceptA] = [(idxB, idxA)]
                else:
                    try:
                        cols[conceptA, conceptB] += [(idxA, idxB)]
                    except KeyError:
                        cols[conceptA, conceptB] = [(idxA, idxB)]
    return cols
        

def write_colexifications(cols, concepts, wordlist, filename=''):
    
    if not filename:
        filename=wordlist['iso']+'-'+wordlist['variety']+'.cols.tsv'

    with open(filename, 'w') as f:
        for c1, c2 in combinations(concepts, r=2):
            if (c1,c2) in cols:
                f.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\n'.format(
                    wordlist['iso'] + '-'+wordlist['variety'],
                    c1,
                    c2,
                        len(cols[c1,c2]),
                        len(cols[c1,c1]),
                        len(cols[c2,c2])
                        ))
            else:
                if (c1,c1) in cols and (c2,c2) in cols:
                    f.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\n'.format(
                        wordlist['iso'] + '-' + wordlist['variety'],
                        c1,
                        c2,
                        0,
                        len(cols[c1,c1]),
                        len(cols[c2,c2])
                        ))
                else:
                    f.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\n'.format(
                        wordlist['iso'] + '-' + wordlist['variety'],
                        c1,
                        c2,
                        0,
                        len(cols[c1,c1]),
                        len(cols[c2,c2])
                        ))
                    

def make_language_map(data):
    """
    Create geojson map of the data, with additional information.
    """
    points = []
                
    
    for did, meta in data.items():
        try:
            lat,lon = meta['latitude'], meta['longitude']
            point = geojson.Point((lon, lat))
            if meta['size'] < 800: marker_color = '#00ff00'
            elif meta['size'] < 1200: marker_color = '#ff00ff'
            else: marker_color = '#0000ff'
            
            feature = geojson.Feature(geometry=point,
                    properties={
                        "language":meta['name'],
                        "coverage":meta['size'],
                        "family":meta['family'],
                        "area":meta['macroarea'],
                        "marker-size":'small',
                        "marker-color" : marker_color
                        }
                    )
            points += [feature]
        except:
            print("problems writing {0}...".format(did))
    return geojson.FeatureCollection(points)
        

