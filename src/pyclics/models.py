# coding: utf8
from collections import OrderedDict, defaultdict
import html
from pathlib import Path

import attr
import geojson
import networkx as nx

__all__ = ['Form', 'Concept', 'Variety', 'Network']


@attr.s
class WithGid(object):
    id = attr.ib()
    source = attr.ib()

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

    def as_geojson(self):
        if self.latitude is None or self.longitude is None:
            kw = {}
        else:
            kw = {'geometry': geojson.Point((self.longitude, self.latitude))}

        return geojson.Feature(
            properties={
                "name": self.name,
                "language": self.name,
                "family": self.family,
                "area": self.macroarea,
                "variety": "std",
                "key": self.gid,
                "glottocode": self.glottocode,
                "source": self.source,
                "lon": self.longitude,
                "lat": self.latitude,
            },
            **kw)


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

    def as_node_attrs(self):
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
            ('Families', ';'.join(self.families)),
            ('ConcepticonId', self.id)
        ])


@attr.s
class Network(object):
    graphname = attr.ib()
    threshold = attr.ib()
    edgefilter = attr.ib()
    graphdir = attr.ib(convert=lambda s: Path(str(s)))

    @property
    def fname(self):
        return self.graphdir / '{0.graphname}-{0.threshold}-{0.edgefilter}.gml'.format(self)

    def save(self, graph):
        with self.fname.open('w') as fp:
            fp.write('\n'.join(html.unescape(line) for line in nx.generate_gml(graph)))
        return self.fname

    @property
    def graph(self):
        def lines():
            for line in self.fname.open():
                yield line.encode('ascii', 'xmlcharrefreplace').decode('utf-8')
        return nx.parse_gml(''.join(lines()))

    def components(self, graph=None):
        return sorted(nx.connected_components(graph or self.graph))

    def communities(self, graph=None):
        comms = defaultdict(list)
        for node, data in (graph or self.graph).nodes(data=True):
            if 'infomap' not in data:
                continue
            comms[data['infomap']].append(node)
        return comms
