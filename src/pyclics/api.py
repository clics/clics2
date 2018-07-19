# coding: utf8
from __future__ import unicode_literals, print_function, division
import json

from clldutils.apilib import API
from clldutils.path import write_text
from clldutils.dsv import UnicodeWriter
from clldutils.misc import lazyproperty
from clldutils import jsonlib

from pyclics.db import Database
from pyclics.models import Network


class Clics(API):
    _log = None

    def existing_dir(self, *comps):
        d = self.path()
        comps = list(comps)
        while comps:
            d = d.joinpath(comps.pop(0))
            if not d.exists():
                d.mkdir()
            assert d.is_dir()
        return d

    @lazyproperty
    def db(self):
        return Database(self.path('clics.sqlite'))

    def file_written(self, p):
        if self._log:
            self._log.info('{0} written'.format(p))

    def csv_writer(self, comp, name, delimiter=',', suffix='csv'):
        p = self.existing_dir(comp).joinpath('{0}.{1}'.format(name, suffix))
        self.file_written(p)
        return UnicodeWriter(p, delimiter=delimiter)

    def json_dump(self, obj, *path):
        p = self.path(*path)
        jsonlib.dump(obj, p, indent=2)
        self.file_written(p)

    def write_js_var(self, var_name, var, *path):
        p = self.path(*path)
        write_text(p, 'var ' + var_name + ' = ' + json.dumps(var, indent=2) + ';')
        self.file_written(p)

    def save_graph(self, graph, network, threshold=None, edgefilter=None):
        if not isinstance(network, Network):
            assert threshold is not None and edgefilter is not None
            network = Network(network, threshold, edgefilter)
        self.file_written(network.save(graph))

    def load_graph(self, network, threshold=None, edgefilter=None):
        if not isinstance(network, Network):
            assert threshold is not None and edgefilter is not None
            network = Network(
                network, threshold, edgefilter, graphdir=self.path('output', 'graphs'))
        return network.load()

    def load_network(self, nname, threshold=None, edgefilter=None):
        return Network(
            nname, threshold, edgefilter, graphdir=self.path('output', 'graphs'))
