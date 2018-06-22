# coding: utf8
from __future__ import unicode_literals, print_function, division
import json

import pytest
from clldutils.path import Path


md = {
    '_concepts': 1,
    '_varieties': 1,
    'vid': {
        'glottocode': 'abcd1234'
    }
}


cldf_md = {}


@pytest.fixture
def repos(tmpdir):
    cldf = tmpdir.mkdir('cldf')
    cldf = cldf.mkdir('test')
    cldf.join('cldf-metadata.json').write(json.dumps(cldf_md))
    gl = tmpdir.mkdir('languoids')
    gl.mkdir('tree')
    ds = tmpdir.mkdir('datasets')
    ds = ds.mkdir('test')
    ds.join('md.json').write(json.dumps(md))
    return Path(str(tmpdir))
