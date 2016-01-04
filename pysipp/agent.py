'''
Wrappers for user agents which apply sensible cmdline arg defaults
'''
from os import path
from distutils import spawn
from collections import namedtuple, OrderedDict
from . import command, launch, plugin
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

    def is_client(self):
        return 'uac' in self.name.lower()

    def is_server(self):
        return 'uas' in self.name.lower()


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

    # override with user settings
    defaults.update(kwargs)
    ua = UserAgent(defaults)

    # call pre defaults hook
    plugin.mng.hook.pysipp_pre_ua_defaults(ua=ua)

    # apply defaults
    set_paths(ua, logdir or ua.logdir)  # assign output file paths

    # call post defaults hook
    plugin.mng.hook.pysipp_post_ua_defaults(ua=ua)

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


class MultiSetter(OrderedDict):
    """A OrderedDict which applies attr sets to all values
    """
    @classmethod
    def from_iter(cls, itr):
        inst = cls()
        inst._init = True  # mark instantiation complete
        # insert items by name
        for item in itr:
            inst[item.name] = item

        return inst

    def __setattr__(self, name, value):
        # multi-setattr all items after init is complete
        if hasattr(self, '_init'):
            for agent in self.values():
                setattr(agent, name, value)

        # default impl
        object.__setattr__(self, name, value)



class Scenario(object):
    """Wraps user agents as a collection for configuration,
    routing, and launching by hooks. It is callable and can be optionally
    be invoked asynchronously.
    """
    def __init__(self, agents, confpy=None):
        self._agents = agents
        self.agents = MultiSetter.from_iter(agents)
        self.clients = MultiSetter.from_iter(a for a in agents if a.is_client())
        self.servers = MultiSetter.from_iter(a for a in agents if a.is_server())
        self.confpy = confpy

    @property
    def name(self):
        """Attempt to extract a name from a combination of scenario directory
        and script names
        """
        dirnames = []
        for agent in self.agents.values():
            if agent.scen_file:
                dirnames.append(path.basename(path.dirname(agent.scen_file)))
            else:
                dirnames.append(agent.scen_name)

        # concat dirnames if scripts come from separate dir locations
        if len(set(dirnames)) > 1:
            return '_'.join(dirnames)

        return dirnames[0]

    def __call__(self, block=True, timeout=180, runner=None, **kwargs):
        return plugin.mng.hook.pysipp_run_protocol(
            scen=self, block=block, timeout=timeout, runner=runner, **kwargs
        )
