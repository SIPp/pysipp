import os.path

import pytest

from pysipp import utils


def test_load_mod(scendir):
    confpy = os.path.join(scendir, "default_with_confpy", "pysipp_conf.py")
    assert utils.load_mod(confpy)


def test_load_mod_ko():
    with pytest.raises(FileNotFoundError):
        utils.load_mod("not_here.py")
