# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyclics.util import *
from pyclics.models import Form


def test_clean_dir(tmpdir, mocker):
    d = tmpdir.join('d')
    assert not d.check()
    clean_dir(str(d))
    assert d.check()

    d.join('f').write('text')
    assert d.join('f').check()
    log = mocker.Mock()
    clean_dir(str(d), log=log)
    assert log.info.called
    assert not d.join('f').check()


def test_colexification():
    formA = Form('', '', 'xy', 'abcd', '', '1', '', '', '')
    formB = Form('', '', 'yz', 'abcd', '', '2', '', '', '')
    res = full_colexification([formA, formB])
    assert len(res['abcd']) == 2
