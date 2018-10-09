# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyclics.util import *
from pyclics.models import Form


def test_colexification():
    formA = Form('', '', 'xy', 'abcd', '', '1', '', '', '')
    formB = Form('', '', 'yz', 'abcd', '', '2', '', '', '')
    res = full_colexification([formA, formB])
    assert len(res['abcd']) == 2
