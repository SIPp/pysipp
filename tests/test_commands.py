'''
Command generation
'''
import pytest
from pysipp.command import SippCmd
from pysipp import utils

log = utils.get_logger()


def test_bool_field():
    cmd = SippCmd()
    with pytest.raises(ValueError):
        cmd.rtp_echo = 'doggy'

    assert '-rtp_echo' not in cmd.render()
    cmd.rtp_echo = True
    assert '-rtp_echo' in cmd.render()


def test_dict_field():
    cmd = SippCmd()
    assert isinstance(cmd.key_vals, dict)

    # one entry
    cmd.key_vals['doggy'] = 100
    assert '-key doggy 100' in cmd.render()

    # two entries
    cmd.key_vals['kitty'] = 200
    assert '-key kitty 200' in cmd.render()
    assert '-key kitty 200' in cmd.render() and\
        '-key doggy 100' in cmd.render()

    # three entries
    cmd.key_vals['mousey'] = 300
    assert '-key kitty 200' in cmd.render() and\
        '-key doggy 100' in cmd.render() and\
        '-key mousey 300' in cmd.render()

    log.debug("cmd is '{}'".format(cmd.render()))

    # clear all
    cmd.key_vals.clear()
    assert '-key' not in cmd.render()
