# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.apilib import API
from clldutils.path import write_text
from clldutils.dsv import UnicodeWriter
from clldutils.misc import lazyproperty

from pyclics.db import Database
from pyclics.models import Network


class Clics(API):
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

    def csv_writer(self, comp, name, delimiter=',', suffix='csv'):
        return UnicodeWriter(
            self.existing_dir(comp).joinpath('{0}.{1}'.format(name, suffix)),
            delimiter=delimiter)

    def write_md_table(self, comp, name, title, table, log):
        p = self.path(comp, '{0}.md'.format(name))
        write_text(p, '# {0}\n\n{1}'.format(title, table.render(condensed=False)))
        log.info('{0} written'.format(p))

    def save_graph(self, graph, network, threshold=None, edgefilter=None, log=None):
        if not isinstance(network, Network):
            assert threshold is not None and edgefilter is not None
            network = Network(network, threshold, edgefilter)
        network.save(graph)
        if log:
            log.info('Network {0} saved'.format(network))

    def load_graph(self, network, threshold=None, edgefilter=None):
        if not isinstance(network, Network):
            assert threshold is not None and edgefilter is not None
            network = Network(
                network, threshold, edgefilter, graphdir=self.path('output', 'graphs'))
        return network.load()

    def load_network(self, nname, threshold=None, edgefilter=None):
        return Network(
            nname, threshold, edgefilter, graphdir=self.path('output', 'graphs'))
