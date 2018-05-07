# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, Counter
from itertools import combinations, groupby
import geojson
import unidecode
import tqdm

from six import text_type
from clldutils.dsv import UnicodeWriter
from clldutils.misc import slug as _slug
from clldutils import jsonlib
from clldutils.path import Path
from pycldf.dataset import Wordlist
import pyclics

def pb(iterable=None, **kw):
    kw.setdefault('leave', False)
    return tqdm.tqdm(iterable=iterable, **kw)


def clics_path(*comps):
    return Path(pyclics.__file__).parent.parent.joinpath(*comps)


def load_concepticon(clics_api, concepticon_api):
    concepticon = {cs.id: cs.__dict__ for cs in concepticon_api.conceptsets.values()}
    for a, b, c in clics_api.csv_reader(Path('output', 'metadata'), 'semantic_fields'):
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


def lexibank2clics(lexibank_dir, clics_dir, languoids, existing=True):
    wl = Wordlist.from_metadata(lexibank_dir.joinpath('cldf', 'cldf-metadata.json'))
    varieties = {l['ID']: l for l in wl['LanguageTable'] if l['glottocode']}
    concepts = {l['ID']: l for l in wl['ParameterTable'] if l['conceptset']}
    count, gcodes = Counter(), set()
    md = {
            '_concepts': len(concepts),
            '_varieties': len(varieties)
            }
    forms = sorted(wl['FormTable'], key=lambda r: r['Language_ID'])
    for lid, forms in pb(
            groupby(forms, lambda r: r['Language_ID']), 
            desc='loading data', 
            total=len(list(groupby(forms, lambda r: r['Language_ID'])))
            ):
        if lid not in varieties:
            # A variety which isn't mapped to glottolog.
            continue
        variety = varieties[lid]
        if variety['glottocode'] not in languoids:
            continue
        forms = [form for form in forms if form['Parameter_ID'] in concepts]
        languoid = languoids[variety['glottocode']]
        if languoid.family and languoid.family.name == 'Bookkeeping':
            continue
    
        if not languoid.latitude and existing:
            while languoid.latitude is None and languoid.lineage:
                languoid = languoids[languoid.lineage.pop()[1]]
            if languoid.latitude is None:
                continue

        meta = dict(
            name=variety['name'],
            glottocode=variety['glottocode'],
            source=lexibank_dir.name,
            classification=', '.join([a[0] for a in languoid.lineage]),
            macroarea=[a.name for a in languoid.macroareas],
            latitude=languoid.latitude,
            longitude=languoid.longitude,
            identifier=lid,
            family=languoid.lineage[0][0] if languoid.lineage else variety['glottocode'])
        count[lid] = 0
        gcodes.add(variety['glottocode'])
        with UnicodeWriter(clics_dir.joinpath('{0}.csv'.format(slug(lid)))) as writer:
            writer.writerow([
                'Doculect_id',
                'Language_ID',
                'Language_name',
                'Parameter_name',
                'Parameter_ID',
                'Value',
                'Clics_Value',
                'Source_ID'])
            for form in forms:
                concept = concepts[form['Parameter_ID']]
                latin_val = slug(unidecode.unidecode(form['Value']))
                if latin_val:
                    count.update([lid])
                    writer.writerow([
                        meta['identifier'],
                        meta['glottocode'],
                        meta['name'],
                        concept['gloss'],
                        concept['conceptset'],
                        form['Value'],
                        latin_val,
                        form['ID'],
                    ])
        meta['size'] = count[lid]
        md[slug(lid)] = meta
    jsonlib.dump(md, clics_dir.joinpath('md.json'), indent=4)
    return count, len(gcodes), len(concepts)

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
                "name": meta['name'],
                "language": meta['name'],
                "coverage": meta['size'],
                "family": meta['family'],
                "area": meta['macroarea'],
                "variety": "std",
                "key": meta['identifier'],
                "glottocode": meta['glottocode'],
                "source": meta['source'],
                "marker-size": 'small',
                "lon": meta['longitude'],
                "lat": meta['latitude'],
                "marker-color": marker_color})

    return geojson.FeatureCollection([_feature(m) for m in data.values()])
