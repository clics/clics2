# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict
import tqdm

from clldutils.path import Path, rmtree
import pyclics


def pb(iterable=None, **kw):
    kw.setdefault('leave', False)
    return tqdm.tqdm(iterable=iterable, **kw)


def clics_path(*comps):
    return Path(pyclics.__file__).parent.parent.parent.joinpath(*comps)


def clean_dir(d, log=None):
    if d.exists():
        rmtree(d)
        if log:
            log.info('recreated {0}'.format(d))
    d.mkdir()
    return d


def full_colexification(forms):
    """
    Calculate all colexifications inside a wordlist.

    :param forms: The forms of a wordlist.

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
    for form in forms:
        if form.clics_form and form.concepticon_id:
            cols[form.clics_form].append(form)
    return cols
