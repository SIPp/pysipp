"""
Command generation
"""
import pytest
from pysipp.command import SippCmd
from pysipp import utils

log = utils.get_logger()


def test_bool_field():
    cmd = SippCmd()
    with pytest.raises(ValueError):
        cmd.rtp_echo = "doggy"

    assert "-rtp_echo" not in cmd.render()
    cmd.rtp_echo = True
    assert "-rtp_echo" in cmd.render()
    assert type(cmd).rtp_echo is not cmd.rtp_echo


def test_dict_field():
    cmd = SippCmd()
    assert isinstance(cmd.key_vals, dict)

    # one entry
    cmd.key_vals["doggy"] = 100
    assert "-key doggy '100'" in cmd.render()

    # two entries
    cmd.key_vals["kitty"] = 200
    assert "-key kitty '200'" in cmd.render()
    assert "-key kitty '200'" in cmd.render() and "-key doggy '100'" in cmd.render()

    # three entries
    cmd.key_vals["mousey"] = 300
    assert (
        "-key kitty '200'" in cmd.render()
        and "-key doggy '100'" in cmd.render()
        and "-key mousey '300'" in cmd.render()
    )

    log.debug("cmd is '{}'".format(cmd.render()))

    # override entire dict
    cmd.key_vals = {
        "mousey": 300,
        "doggy": 100,
    }
    assert "-key kitty '200'" not in cmd.render()
    assert "-key doggy '100'" in cmd.render() and "-key mousey '300'" in cmd.render()

    # clear all
    cmd.key_vals.clear()
    assert "-key" not in cmd.render()


def test_list_field():
    cmd = SippCmd()
    assert cmd.info_files is None

    # one entry
    cmd.info_files = ["100"]
    assert "-inf '100'" in cmd.render()

    # two entries
    cmd.info_files = ["100", "200"]
    assert "-inf '100' -inf '200'" in cmd.render()

    # clear all
    del cmd.info_files[:]
    assert "-inf" not in cmd.render()

    # three entries - two via 'info_files' and one via 'info_file'
    cmd.info_files = ["100", "200"]
    cmd.info_file = "300"
    assert "-inf '300' -inf '100' -inf '200'" in cmd.render()

    # clear all
    cmd.info_file = ""
    cmd.info_files[:] = []
    assert "-inf" not in cmd.render()


def test_prefix():
    cmd = SippCmd()
    pre = "doggy bath"
    cmd.prefix = pre
    # single quotes are added
    assert cmd.render() == "'{}'".format(pre) + " "


@pytest.mark.parametrize(
    "host, port, command",
    [
        (None, None, ""),
        ("127.0.0.1", 5060, "-rsa '127.0.0.1':'5060' "),
        ("::1", None, "-rsa '[::1]':'5060' "),
        ("example.com", None, "-rsa 'example.com':'5060' "),
    ],
)
def test_addr_field(host, port, command):
    cmd = SippCmd()
    cmd.proxy_host = host
    cmd.proxy_port = port
    assert cmd.render() == command
