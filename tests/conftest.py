# coding: utf8
from __future__ import unicode_literals, print_function, division
import os
from tempfile import NamedTemporaryFile
from pathlib import Path

import pytest
from pylexibank.dataset import Dataset

from pyclics.db import Database


@pytest.fixture
def repos(tmpdir):
    gl = tmpdir.mkdir('languoids')
    gl.mkdir('tree')
    concepticon = tmpdir.mkdir('concepticondata')
    concepticon.join('concepticon.tsv').write('')
    return Path(str(tmpdir))


@pytest.fixture(scope='session')
def dataset():
    class ClicsDataset(Dataset):
        dir = str(Path(__file__).parent / 'dataset')

    return ClicsDataset()


@pytest.fixture(scope='session')
def db(dataset):
    tmp = NamedTemporaryFile(delete=False)
    db = Database(tmp.name)
    db.create(exists_ok=True)
    db.load(dataset)
    with db.connection() as conn:
        conn.execute("update LanguageTable set glottocode = 'glot1234', family='family'")
        conn.execute("""\
update ParameterTable set 
    concepticon_id = cast(random() as text),
    concepticon_gloss = 'gloss',
    ontological_category = 'oc',
    semantic_field = 'sf'""")
        conn.commit()
    yield db
    os.remove(tmp.name)
