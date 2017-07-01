from mock import Mock
from clldutils.testing import WithTempDir, capture

from pyclics.api import Clics
from pyclics import commands


class Tests(WithTempDir):
    def _args(self):
        return Mock(api=Clics(self.tmp_path()))

    def test_list(self):
        with capture(commands.list_, self._args()) as out:
            self.assertIn('ids', out)
