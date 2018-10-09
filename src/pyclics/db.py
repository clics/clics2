# coding: utf8
import string

from unidecode import unidecode
from pylexibank.db import Database as Database_

from pyclics.models import Form, Concept, Variety

__all__ = ['Database']

# unidecode converts "ə" to "@"
ALLOWED_CHARACTERS = string.ascii_letters + string.digits + '@'


def clics_form(word):
    return ''.join(c for c in unidecode(word) if c in ALLOWED_CHARACTERS).lower()


class Database(Database_):
    """
    The CLICS database adds a column `clics_form` to lexibank's FormTable.
    """
    Database_.sql["concepts_by_dataset"] = """\
SELECT
    ds.id, count(distinct p.concepticon_id), count(distinct p.name)
FROM
    dataset as ds, parametertable as p, formtable as f
WHERE
    ds.id = p.dataset_id and f.dataset_id = ds.id and f.parameter_id = p.id
GROUP BY ds.id"""

    @property
    def datasets(self):
        return sorted(r[0] for r in self.fetchall("select id from dataset"))

    def update_schema(self):
        Database_.update_schema(self)
        for tname, cname, type_ in [
            ('FormTable', 'clics_form', 'TEXT'),
        ]:
            if cname not in self.tables[tname]:
                with self.connection() as conn:
                    conn.execute("ALTER TABLE {0} ADD COLUMN `{1}` {2}".format(
                        tname, cname, type_))

    def update_row(self, table, keys, values):
        if table == 'FormTable':
            d = dict(zip(keys, values))
            keys = list(keys) + ['`clics_form`']
            values = list(values) + [clics_form(d['`Form`'])]
        return keys, values

    @property
    def varieties(self):
        return [Variety(*row) for row in self.fetchall("""\
select
    l.id, l.dataset_id, l.name, l.glottocode, l.family, l.macroarea, l.longitude, l.latitude
from
    languagetable as l
where
    l.glottocode is not null
    and l.family != 'Bookkeeping'
    and exists (
        select 1 from formtable as f where f.language_id = l.id and f.dataset_id = l.dataset_id
    )
group by
    l.id, l.dataset_id
order by
    l.dataset_id, l.id""")]

    def iter_wordlists(self, varieties):
        languages = {(v.source, v.id): v for v in varieties}
        for (dsid, vid), v in sorted(languages.items()):
            forms = [Form(*row) for row in self.fetchall("""
select
    f.id, f.dataset_id, f.form, f.clics_form,
    p.name, p.concepticon_id, p.concepticon_gloss, p.ontological_category, p.semantic_field
from
    formtable as f, parametertable as p
where
    f.parameter_id = p.id
    and f.dataset_id = p.dataset_id
    and p.concepticon_id is not null
    and f.language_id = ?
    and f.dataset_id = ?
order by
    f.dataset_id, f.language_id, p.concepticon_id
""", params=(vid, dsid))]
            assert forms
            yield v, forms

    def _lids_by_concept(self):
        return {r[0]: sorted(set(r[1].split())) for r in self.fetchall("""\
select
    p.concepticon_id, group_concat(f.dataset_id || '-' || f.language_id, ' ')
from
    parametertable as p, formtable as f
where
    f.parameter_id = p.id and f.dataset_id = p.dataset_id
group by
    p.concepticon_id
""")}

    def _fids_by_concept(self):
        return {r[0]: sorted(set(r[1].split('|') if r[1] else '')) for r in self.fetchall("""\
select
    p.concepticon_id, group_concat(l.family, '|')
from
    parametertable as p, formtable as f, languagetable as l
where
    f.parameter_id = p.id
    and f.dataset_id = p.dataset_id
    and f.language_id = l.id
    and f.dataset_id = l.dataset_id
group by
    p.concepticon_id
""")}

    def _wids_by_concept(self):
        return {r[0]: sorted(set(r[1].split())) for r in self.fetchall("""\
select
    p.concepticon_id, group_concat(f.dataset_id || '-' || f.id, ' ')
from
    parametertable as p, formtable as f
where
    f.parameter_id = p.id and f.dataset_id = p.dataset_id
group by
    p.concepticon_id
""")}

    def iter_concepts(self):
        concepts = [Concept(*row) for row in self.fetchall("""\
select distinct
    concepticon_id, concepticon_gloss, ontological_category, semantic_field
from
    parametertable
where
    concepticon_id is not null""")]
        lids = self._lids_by_concept()
        fids = self._fids_by_concept()
        wids = self._wids_by_concept()

        for c in concepts:
            c.varieties = lids.get(c.id, [])
            c.families = fids.get(c.id, [])
            c.forms = wids.get(c.id, [])
            yield c
