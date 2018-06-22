# coding: utf8
from __future__ import unicode_literals, print_function, division
import pickle
from collections import OrderedDict, defaultdict
try:  # pragma: no cover
    from HTMLParser import HTMLParser
    html = HTMLParser()
except ImportError:  # pragma: no cover
    import html

import attr
import geojson
from clldutils.misc import UnicodeMixin
from clldutils.path import write_text, read_text
import networkx as nx

from pyclics.util import clics_path

__all__ = ['Form', 'Concept', 'Variety', 'Network']


@attr.s
class WithGid(object):
    id = attr.ib()
    source = attr.ib()

    def asdict(self):
        return attr.asdict(self)

    @property
    def gid(self):
        return '{0}-{1}'.format(self.source, self.id)


@attr.s
class Variety(WithGid):
    name = attr.ib()
    glottocode = attr.ib()
    family = attr.ib()
    macroarea = attr.ib()
    longitude = attr.ib()
    latitude = attr.ib()
    size = attr.ib()

    def as_stats_dict(self):
        return OrderedDict([
            ('Identifier', self.gid),
            ('Language_name', self.name),
            ('Language_ID', self.glottocode),
            ('Family', self.family),
            ('Longitude', self.longitude),
            ('Latitude', self.latitude)
        ])

    def as_geojson(self):
        if self.latitude is None or self.longitude is None:
            return
        if self.size < 800:
            marker_color = '#00ff00'
        elif self.size < 1200:
            marker_color = '#ff00ff'
        else:
            marker_color = '#0000ff'
        return geojson.Feature(
            geometry=geojson.Point((self.longitude, self.latitude)),
            properties={
                "name": self.name,
                "language": self.name,
                "coverage": self.size,
                "family": self.family,
                "area": self.macroarea,
                "variety": "std",
                "key": self.gid,
                "glottocode": self.glottocode,
                "source": self.source,
                "marker-size": 'small',
                "lon": self.longitude,
                "lat": self.latitude,
                "marker-color": marker_color})


@attr.s
class Form(WithGid):
    form = attr.ib()
    clics_form = attr.ib()
    gloss = attr.ib()
    concepticon_id = attr.ib()
    concepticon_gloss = attr.ib()
    ontological_category = attr.ib()
    semantic_field = attr.ib()


@attr.s
class Concept(object):
    id = attr.ib()
    gloss = attr.ib()
    ontological_category = attr.ib()
    semantic_field = attr.ib()
    forms = attr.ib(default=attr.Factory(list))
    varieties = attr.ib(default=attr.Factory(list))
    families = attr.ib(default=attr.Factory(list))

    def asdict(self):
        return OrderedDict([
            ('ID', self.id),
            ('Gloss', self.gloss),
            ('Semanticfield', self.semantic_field),
            ('Category', self.ontological_category),
            ('FamilyFrequency', len(self.families)),
            ('LanguageFrequency', len(self.varieties)),
            ('WordFrequency', len(self.forms)),
            ('Words', ';'.join(self.forms)),
            ('Languages', ';'.join(self.varieties)),
            ('Families', ';'.join(self.families))])

    def as_node_attrs(self):
        res = self.asdict()
        res['ConcepticonId'] = self.id
        return res


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
            if 'infomap' not in data:
                break
            comms[data['infomap']] += [node]
        return comms
