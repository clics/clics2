"""functions for loading datasets"""
from pyclics.utils import *
from glob import glob
from clldutils.dsv import UnicodeReader
from pyglottolog.api import Glottolog

glottolog = Glottolog()
concepticon = load_concepticon()

def load_ids(verbose=False):
    """Load all the current IDS data"""
    files = glob(lexibank_path('ids', 'cldf', '*.csv'))
    for i, f in enumerate([x for x in files if 'cognates.csv' not in x]):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        try:
            wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=False,
                    conceptcolumn='Parameter_name',
                    source='IDS')
            if wl:
                write_clics_wordlist(wl, clics_path('cldf',
                    wl['meta']['identifier']+'_'+str(i+1)+'.csv'))
            else:
                print('[!] Invalid glottolog-code for the language {0}'.format(
                    f))
        except IndexError:
            print("[!] Bad format in file {0}".format(f))



def load_wold(verbose=False):
    files = glob(lexibank_path('wold', 'cldf', '*.csv'))
    for i, f in enumerate([x for x in files if 'cognates.csv' not in x]):
        if verbose: print('[{1}] Converting file {0}...'.format(os.path.split(f)[-1], i+1))
        wl = read_cldf_wordlist(f, glottolog=glottolog, metadata=False,
                conceptcolumn='Parameter_name',
                source='WOLD')
        if wl:
            write_clics_wordlist(wl, clics_path('cldf',
                wl['meta']['identifier']+'-'+str(i+1)+'.csv'))
        else:
            print('[!] Invalid glottolog-code for the language {0}'.format(
                f))


def load_multilanguage_cldf(dataset, filename, source, conceptcolumn,
        languagecolumn, verbose=False):
    with UnicodeReader(lexibank_path(
                dataset, 'cldf', filename)) as reader:
        data = list(reader)
        header = data[0]
        lines = data[1:]
        lidx = header.index(languagecolumn)
        lines = sorted(lines, key=lambda x: x[lidx])
        current_language = lines[0][lidx]
        current_lines = [header]
        count = 1
        for line in lines:
            next_language = line[lidx]
            if next_language != current_language:
                if verbose: print('[{1}] converting language {0}...'.format(
                    current_language, count))
                count += 1
                wl = read_cldf_wordlist(current_lines, glottolog=glottolog,
                        metadata=False, conceptcolumn='Parameter_name',
                        source=source
                        )
                if wl:
                    write_clics_wordlist(wl, clics_path('cldf',
                        wl['meta']['identifier']+'_'+str(count-1)+'.csv'))
                else:
                    print('[!] Invalid glottolog-code for the language {0}'.format(
                    current_language))
                current_lines = [header, line]
                current_language = next_language
            else:
                current_lines += [line]


def load_nelex(verbose=False):
    load_multilanguage_cldf('northeuralex', 'northeuralex.csv', 'nelex',
            'Parameter_name', 'Language_name', verbose=verbose)


def load_baidial(verbose=False):

    load_multilanguage_cldf('baidial', 'baidial.csv', 'baidial', 'Parameter_name',
            'Language_name', verbose=verbose)


def load_kraft(verbose=False):
    load_multilanguage_cldf('kraft1981', 'kraft1981.csv', 'kraft1981',
            'Parameter_name', 'Language_name', verbose=verbose)


def load_tryon(verbose=False):
    load_multilanguage_cldf('tryonhackman1983', 'tryonhackman1983.csv',
            'tryonhackman1983', 'Parameter_name', 'Language_name',
            verbose=verbose)


def load_huber(verbose=False):
    load_multilanguage_cldf('huberandreed', 'huberandreed.csv',
            'huberandreed', 'Parameter_name', 'Language_name',
            verbose=verbose)
