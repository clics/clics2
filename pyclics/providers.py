# coding: utf8
"""functions for loading datasets"""
from __future__ import unicode_literals, print_function, division
from itertools import groupby

from clldutils.dsv import reader
from pyglottolog.api import Glottolog


class Loader(object):
    def __init__(self, api, lexibank_repos, glottolog_repos, log=None):
        self.api = api
        self.glottolog = Glottolog(glottolog_repos)
        self.lexibank_repos = lexibank_repos
        self.log = log
        self.languoids = {}

    @property
    def cldf_path(self):
        return self.lexibank_repos.joinpath('datasets', self.id(), 'cldf')

    @classmethod
    def id(cls):
        return cls.__name__.lower()

    def convert(self, f, index, name, conceptcolumn='Parameter_name', source=None):
        self.log.debug('[{1}] Converting {0}...'.format(name, index))
        wl = self.api.read_cldf_file(
            f,
            self.glottolog,
            metadata=False,
            conceptcolumn=conceptcolumn,
            source=source or self.__class__.__name__,
            languoids=self.languoids)
        if wl:
            self.api.write_wordlist(
                wl, '{0}_{1}'.format(wl['meta']['identifier'], index))
            return True
        self.log.warn('Invalid glottocode for the language {0}'.format(name))
        return False

    def __call__(self):
        raise NotImplemented()


class IDS(Loader):
    def __call__(self):
        """Load all the current IDS data"""
        self.languoids = {l.id: l for l in self.glottolog.languoids()}
        count = 0
        for i, f in enumerate(
                [p for p in self.cldf_path.glob('*.csv') if p.stem != 'cognates']):
            try:
                if self.convert(f, i + 1, f.name):
                    count += 1
            except IndexError:
                self.log.warn("Bad format in file {0}".format(f))
        return count


class WOLD(IDS):
    pass


class MultiLanguageLoader(Loader):
    def __call__(self):
        return self.convert_multi()

    def convert_multi(self, source=None):
        lines = list(reader(self.cldf_path.joinpath('{0}.csv'.format(self.id()))))
        header = lines.pop(0)
        lidx = header.index('Language_name')
        lines = sorted(lines, key=lambda x: x[lidx])

        count = 0
        for i, (language, llines) in enumerate(groupby(
                sorted(lines, key=lambda x: x[lidx]), lambda x: x[lidx])):
            if self.convert([header] + list(llines), i + 1, language, source=source):
                count += 1
        return count


class NorthEuraLex(MultiLanguageLoader):
    def __call__(self):
        return self.convert_multi('nelex')


class baidial(MultiLanguageLoader):
    pass


class kraft1981(MultiLanguageLoader):
    pass


class tryonhackman1983(MultiLanguageLoader):
    pass


class huberandreed(MultiLanguageLoader):
    pass


LOADER = [IDS, WOLD, NorthEuraLex, baidial, kraft1981, tryonhackman1983, huberandreed]
