'''
Wrappers for user agents which apply sensible cmdline arg defaults
'''
from os import path
from distutils import spawn
from collections import namedtuple
from . import command, launch
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


class UserAgent(command.SippCmd):
    '''An extension of a SIPp command string which provides
    higher level attributes for assigning input arguments more similar
    to configuration options for a SIP UA.
    '''
    logdir = utils.get_tmpdir()
    runner_type = launch.PopenRunner
    _runner = None

    @property
    def name(self):
        """Compute the name identifier for this agent based the scenario script
        or scenario name
        """
        return self.scen_name or path2namext(self.scen_file)

    @property
    def proxy(self):
        return SocketAddr(self.proxy_addr, self.proxy_port)

    @proxy.setter
    def proxy(self, pair):
        self.proxy_addr, self.proxy_port = pair[0], pair[1]

    @property
    def runner(self):
        if not getattr(self, '_runner', None):
            self._runner = self.runner_type([self])
        return self._runner

    def run(self, **kwargs):
        return self.runner(**kwargs)


def path2namext(filepath):
    if not filepath:
        return None
    name, ext = path.splitext(path.basename(filepath))
    return name


def set_paths(ua, logdir):
    name = ua.name
    for key in 'error calldebug message log screen'.split():
        filename = "{}_file".format(key)
        setattr(ua, filename, path.join(
                logdir, "{}_{}".format(name, filename)))


def ua(logdir=None, **kwargs):
    """Default user agent factory.
    Returns a command string instance with sensible default arguments.
    """
    defaults = {
        'bin_path': spawn.find_executable('sipp'),
        'recv_timeout': 5000,
        'call_count': 1,
        'rate': 1,
    }
    # drop any built-in scen if a script file is provided
    if 'scen_file' in kwargs:
        kwargs.pop('scen_name')

    log.debug("defaults are {} extras are {}".format(
        defaults, kwargs))
    # override xith user settings
    defaults.update(kwargs)
    ua = UserAgent(defaults)

    # call pre defaults hook

    # apply defaults
    # assign output file paths
    set_paths(ua, logdir or ua.logdir)

    # call post defaults hook
    return ua


def server(**kwargs):
    defaults = {
        'scen_name': 'uas',
    }
    # override with user settings
    defaults.update(kwargs)
    return ua(**defaults)


def client(remote_host, remote_port, **kwargs):
    defaults = {
        'scen_name': 'uac',
    }
    # override with user settings
    defaults.update(kwargs)
    assert remote_host and remote_port
    return ua(
        remote_host=remote_host,
        remote_port=remote_port,
        **defaults
    )
