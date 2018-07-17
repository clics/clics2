from __future__ import unicode_literals
import shutil

import pytest

from pyclics.api import Clics
from pyclics import commands
from pyclics import __main__  # noqa


@pytest.fixture
def api(repos, db):
    dbfname = repos.joinpath('clics.sqlite')
    if not dbfname.exists():
        shutil.copy(str(db.fname), str(dbfname))
    return Clics(repos)


def test_load(mocker, tmpdir, repos, dataset):
    tmpdir.join('load').mkdir()
    api = Clics(str(tmpdir.join('load')))
    mocker.patch('pyclics.commands.iter_datasets', lambda: [dataset])
    commands.load(mocker.Mock(
        args=[], api=api, glottolog_repos=str(repos), concepticon_repos=str(repos)))
    commands.load(mocker.Mock(
        args=[], api=api, glottolog_repos=str(repos), concepticon_repos=str(repos), unloaded=True))
    commands.clean(mocker.Mock(args=[], api=api))


def test_list(api, mocker, repos, capsys):
    commands.list_(mocker.Mock(api=api, lexibank_repos=repos, unloaded=True))
    _, _ = capsys.readouterr()

    commands.list_(mocker.Mock(api=api, lexibank_repos=repos, unloaded=False))
    out, err = capsys.readouterr()
    assert '9' in out


def test_workflow(api, mocker, capsys):
    args = mocker.Mock(
        api=api, graphname='g', threshold=1, edgefilter='families', weight='FamilyWeight')
    commands.colexification(args)
    out, err = capsys.readouterr()
    assert 'Concept B' in out

    commands.communities(args)
    commands.subgraph(args)
    commands.articulationpoints(args)
    commands.graph_stats(args)
    out, err = capsys.readouterr()
    assert '499' in out and '480' in out and '209' in out
