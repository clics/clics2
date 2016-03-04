import json
from itertools import combinations
import geojson

def load_glottolog():

    G = json.load(open('glottolog.json'))

    return G

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

def full_colexification(wordlist, key='ids_key', entry='entry', indices='indices', 
        redundant=False):
    
    cols = {}

    # get the key-index
    key_idx = wordlist[0].index(key)
    entry_idx = wordlist[0].index(entry)
    for idxA, idxB in combinations(wordlist[indices],r=2):

        wordA, wordB = wordlist[idxA][entry_idx], wordlist[idxB][entry_idx]
        if wordA == wordB:
            try:
                cols[wordlist[idxA][key_idx], wordlist[idxB][key_idx]] += [[idxA,idxB]]
            except KeyError:
                cols[wordlist[idxA][key_idx], wordlist[idxB][key_idx]] = [[idxA,idxB]]

    # if redundant, add counts for each concept colexified with itself
    if redundant:
        for idx in wordlist[indices]:
            word = wordlist[idx][entry_idx]
            try:
                cols[wordlist[idx][key_idx], wordlist[idx][key_idx]] += [[idx, idx]]
            except:
                cols[wordlist[idx][key_idx], wordlist[idx][key_idx]] = [[idx, idx]]

    
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
            if meta['vocabulary_size'] < 800: marker_color = '#00ff00'
            elif meta['vocabulary_size'] < 1200: marker_color = '#ff00ff'
            else: marker_color = '#0000ff'
            
            feature = geojson.Feature(geometry=point,
                    properties={
                        "language":meta['language_name'],
                        "coverage":meta['vocabulary_size'],
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
        




if __name__ == '__main__':
    wl = read_clics_concept_list('deu_std.csv')
    cols = full_colexification(wl, redundant=True)
    print(len(cols))
    write_colexifications(cols, sorted(set([wl[idx][0] for idx in
        wl['indices']])), wl)

