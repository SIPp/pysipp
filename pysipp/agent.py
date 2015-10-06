'''
Wrappers for user agents which apply sensible cmdline arg defaults
'''
from os import path
from collections import namedtuple
from .command import SippCmd
import utils

log = utils.get_logger()

SocketAddr = namedtuple('SocketAddr', 'ip port')


ERRCODES = {
    # 0: "All calls were successful"
    1: "At least one call failed",
    15: "Process was terminated",
    97: "Exit on internal command. Calls may have been processed",
    99: "Normal exit without calls processed",
    -1: "Fatal error",
    -2: "Fatal error binding a socket",
    -10: "Signalled to stop with SIGUSR1",
    254: "Connection Error: socket already in use",
    255: "Command or syntax error: check stderr output",
}


class UserAgent(object):
    '''A wrapper around a SIPp command string
    '''
    def __init__(self, cmd):
        self._cmd = cmd
        self._name = None
        self._proxy = None

    @property
    def name(self):
        """Compute the name identifier for this agent based the scenario script
        or scenario name
        """
        cmd = self._cmd
        return cmd.scen_name or path2namext(cmd.scen_file)

    def render(self):
        return self._cmd.render()

    @property
    def proxy(self):
        return self._proxy

    @proxy.setter
    def proxy(self, pair):
        self._proxy = SocketAddr(*pair)
        self._cmd.proxy_addr = '[{}]'.format(self._proxy.ip)
        self._cmd.proxy_port = self._proxy.port


spec = [
    # contact info
    '{remote_host}:{remote_port}',
    '-i {local_host}',
    '-p {local_port}',
    '-s {uri_username}',
    '-rsa {proxy_addr}:{proxy_port}',
    '-auth_uri {auth_uri}',
    # sockets and protocols
    '-bind_local {bind_local}',
    '-mi {media_addr}',
    '-mp {media_port}',
    '-t {transport}',
    # scenario config/ctl
    '-sn {scen_name}',
    '-sf {scen_file}',
    '-recv_timeout {recv_timeout}',
    '-d {pause_duration}',
    '-default_behaviors {default_behaviors}',
    '-3pcc {3pcc}',
    # SIP vars
    '-cid_str {cid_str}',
    '-base_cseq {base_cseq}',
    '-ap {auth_password}',
    # load settings
    '-r {rate}',
    '-l {limit}',
    '-m {call_count}',
    '-rp {rate_period}',
    # data insertion
    '-key {key_vals}',
    # files
    '-error_file {error_file}',
    '-calldebug_file {calldebug_file}',
    '-message_file {message_file}',
    '-log_file {log_file}',
    '-inf {info_file}',
    '-screen_file {screen_file}',
    # bool flags
    # '-rtp_echo',
]


def path2namext(filepath):
    name, ext = path.splitext(path.basename(filepath))
    return name


def ua(spec=spec, **kwargs):
    defaults = {
        'recv_timeout': 5000,
        'call_count': 1,
    }

    log.debug("defaults are {} extras are {}".format(
        defaults, kwargs))
    # override with user settings
    defaults.update(kwargs)
    cmd = SippCmd(spec)

    # apply attrs raising erros along the way
    for name, value in defaults.items():
        setattr(cmd, name, value)

    return cmd


def server(**kwargs):
    defaults = {
        'scen_name': 'uas',
    }
    # override with user settings
    defaults.update(kwargs)

    cmd = ua(**defaults)

    return cmd


def client(remote_host, remote_port, **kwargs):
    defaults = {
        'scen_name': 'uac',
    }
    # override with user settings
    defaults.update(kwargs)
    assert remote_host and remote_port

    cmd = ua(
        remote_host=remote_host,
        remote_port=remote_port,
        **defaults
    )

    return cmd
