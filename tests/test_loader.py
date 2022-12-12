"""
Scen dir loading
"""
import os

from pysipp.load import iter_scen_dirs


def test_scendir_loading(scendir):
    dir_list = list(iter_scen_dirs(scendir))
    assert len(dir_list) == 2  # only dirs with xmls


def test_iter_dirs(scendir):
    paths = {
        "default": [True, False],
        "default_with_confpy": [True, True],
        "just_confpy": [False, True],
    }
    for path, xmls, confpy in iter_scen_dirs(scendir):
        expect = paths.get(os.path.basename(path), None)
        if expect:
            assert [bool(xmls), bool(confpy)] == expect
