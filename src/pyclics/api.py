# coding: utf8
import json

from clldutils.apilib import API
from clldutils.path import write_text
from clldutils.dsv import UnicodeWriter
from clldutils.misc import lazyproperty
from clldutils import jsonlib

from pyclics.db import Database
from pyclics.models import Network

__all__ = ['Clics']


class Clics(API):
    _log = None

    def existing_dir(self, *comps, **kw):
        d = self.path()
        comps = list(comps)
        while comps:
            d = d.joinpath(comps.pop(0))
            if not d.exists():
                d.mkdir()
            assert d.is_dir()
        if kw.get('clean'):
            for p in d.iterdir():
                if p.is_file():
                    p.unlink()
        return d

    @lazyproperty
    def db(self):
        return Database(self.path('clics.sqlite'))

    def file_written(self, p):
        if self._log:
            self._log.info('{0} written'.format(p))
        return p

    def csv_writer(self, comp, name, delimiter=',', suffix='csv'):
        p = self.existing_dir(comp).joinpath('{0}.{1}'.format(name, suffix))
        self.file_written(p)
        return UnicodeWriter(p, delimiter=delimiter)

    def json_dump(self, obj, *path):
        p = self.existing_dir(*path[:-1]) / path[-1]
        jsonlib.dump(obj, p, indent=2)
        self.file_written(p)

    def write_js_var(self, var_name, var, *path):
        p = self.path(*path)
        write_text(p, 'var ' + var_name + ' = ' + json.dumps(var, indent=2) + ';')
        self.file_written(p)

    def save_graph(self, graph, network, threshold, edgefilter):
        network = Network(network, threshold, edgefilter, self.existing_dir('graphs'))
        return self.file_written(network.save(graph))

    def load_graph(self, network, threshold, edgefilter):
        return Network(network, threshold, edgefilter, self.existing_dir('graphs')).graph

    def load_network(self, nname, threshold, edgefilter):
        return Network(nname, threshold, edgefilter, self.existing_dir('graphs'))
