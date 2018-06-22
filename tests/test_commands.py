from __future__ import unicode_literals

import pytest

from pyclics.api import Clics
from pyclics import commands


@pytest.fixture
def api(repos):
    return Clics(repos)


def test_list(api, mocker, repos, capsys):
    commands.list_(mocker.Mock(api=api, lexibank_repos=repos, unloaded=True))
    out, err = capsys.readouterr()

    commands.list_(mocker.Mock(api=api, lexibank_repos=repos, unloaded=False))
    out, err = capsys.readouterr()
    assert 'No datasets' in out


def test_load(api, repos, mocker):
    pass
    #commands.load(mocker.Mock(args=[], api=api, glottolog_repos=str(repos)))
