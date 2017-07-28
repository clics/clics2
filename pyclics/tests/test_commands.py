from __future__ import unicode_literals

from mock import Mock
from clldutils.testing import WithTempDir, capture
from clldutils.path import write_text

from pyclics.api import Clics
from pyclics import commands


class Tests(WithTempDir):
    def _args(self, **kw):
        return Mock(api=Clics(self.tmp_path()), **kw)

    def test_list(self):
        self.tmp_path('datasets').mkdir()
        self.tmp_path('datasets', 'ids').mkdir()
        self.tmp_path('datasets', 'ids', 'cldf').mkdir()
        write_text(self.tmp_path('datasets', 'ids', 'cldf', 'cldf-metadata.json'), '{}')
        with capture(commands.list_, self._args(lexibank_repos=self.tmp_path())) as out:
            self.assertIn('ids', out)
