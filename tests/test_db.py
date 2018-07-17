import pytest

from pyclics.db import clics_form


@pytest.mark.parametrize(
    'form,clics',
    [
        ('abc', 'abc'),
        ('abC', 'abc'),
        ('a.bC', 'abc'),
        ('bə', 'b@'),
        ('ábc', 'abc'),
        ('äöü', 'aou'),
    ]
)
def test_clics_form(form, clics):
    assert clics == clics_form(form)


def test_db_queries(db):
    assert len(db.datasets) == 1

    varieties = db.varieties
    assert len(varieties) == 9

    for v, forms in db.iter_wordlists(varieties):
        if v.id == 'Eryuan':
            assert len(forms) == 503
            break
    concepts = list(db.iter_concepts())
    assert len(concepts) == 499
