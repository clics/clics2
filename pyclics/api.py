# coding: utf8
from __future__ import unicode_literals, print_function, division
import pickle
from collections import defaultdict
try:
    from HTMLParser import HTMLParser
    html = HTMLParser()
except ImportError:
    import html

import attr
from clldutils.apilib import API
from clldutils.path import write_text, read_text
from clldutils.dsv import reader, UnicodeWriter
from clldutils.misc import UnicodeMixin
from clldutils import jsonlib
import networkx as nx

from pyclics.util import lexibank2clics, clics_path

@attr.s
class Network(UnicodeMixin):
    graphname = attr.ib()
    threshold = attr.ib()
    edgefilter = attr.ib()
    G = attr.ib(default=None)
    graphdir = attr.ib(default=clics_path('output', 'graphs'))

    def __unicode__(self):
        return '{0.graphname}-{0.threshold}-{0.edgefilter}'.format(self)

    def fname(self, d, ext):
        return d.joinpath('{0}.{1}'.format(self, ext))

    def save(self, graph):
        with open(self.fname(self.graphdir, 'bin').as_posix(), 'wb') as f:
            pickle.dump(graph, f)
        write_text(
            self.fname(self.graphdir, 'gml'),
            '\n'.join(html.unescape(line) for line in nx.generate_gml(graph)))

    def load(self):
        bin = self.fname(self.graphdir, 'bin')
        if bin.exists():
            self.G = pickle.load(open(bin.as_posix(), 'rb'))
            return self.G

        lines = read_text(self.fname(self.graphdir, 'gml')).split('\n')
        lines = [l.encode('ascii', 'xmlcharrefreplace').decode('utf-8') for l in lines]
        self.G = nx.parse_gml('\n'.join(lines))
        return self.G
    
    def components(self):
        if not self.G:
            self.load()
        return sorted(nx.connected_components(self.G))

    def communities(self):
        if not self.G:
            self.load()
        comms = defaultdict(list)
        for node, data in self.G.nodes(data=True):
            if not 'infomap' in data:
                break
            comms[data['infomap']] += [node]
        return comms


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

    def csv_reader(self, comp, name):
        return list(reader(self.path(comp, '{0}.csv'.format(name))))

    def csv_writer(self, comp, name, delimiter=',', suffix='csv'):
        return UnicodeWriter(
            self.existing_dir(comp).joinpath('{0}.{1}'.format(name, suffix)),
            delimiter=delimiter)

    def wordlists(self):
        for dd in self.path('datasets').iterdir():
            if dd.is_dir():
                md = jsonlib.load(dd.joinpath('md.json'))
                for p in dd.glob('*.csv'):
                    D = dict(identifiers=[], meta=md[p.stem])
                    for i, row in enumerate(reader(p)):
                        if i == 0:
                            D[i] = row
                        else:
                            D[row[-1]] = row
                            D['identifiers'].append(row[-1])
                    yield D

    def load(self, lexibank_dir, languoids):
        return lexibank2clics(
            lexibank_dir, self.existing_dir('datasets', lexibank_dir.name), languoids)

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
            network = Network(network, threshold, edgefilter,
                    graphdir=self.path('output', 'graphs'))
        return network.load()

    def load_network(self, nname, threshold=None, edgefilter=None):
        network = Network(nname, threshold, edgefilter,
                graphdir=self.path('output', 'graphs'))
        return network
