'''
Wrappers for user agents which apply sensible cmdline arg defaults
'''
from os import path
from collections import deque, namedtuple
from .command import SippCmd


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
        self._cmd.proxy = '[{}]:{}'.format(*self._proxy)


spec = deque((
    # contact info
    '{remote_host}:{remote_port}',
    '-i {local_host}',
    '-p {local_port}',
    '-recv_timeout {msg_timeout}',
    '-s {uri_username}',
    '-rsa {proxy}',
    # scenario related
    '-sn {scen_name}',
    '-sf {scen_file}',
    # load settings
    '-d {duration}',
    '-r {rate}',
    '-l {limit}',
    '-m {call_count}'
    # call behaviour
    '-base_cseq {base_cseq}',
    '-cid_str {cid_str}',
    # overall behaviour
    '-key {key_vals}',
))


def path2namext(filepath):
    name, ext = path.splitext(path.basename(filepath))
    return name


def ua(spec=spec, **kwargs):
    defaults = {
        'msg_timeout': 5000
    }
    # override with user settings
    defaults.update(kwargs)
    cmd = SippCmd(spec, fields=defaults)

    # apply kwargs raising attr erros along the way
    for name, value in kwargs.items():
        setattr(cmd, name, value)

    return cmd
    # return UserAgent(cmd)


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
