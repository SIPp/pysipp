# Copyright (C) 2015 Tyler Goodlet
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Authors : Tyler Goodlet
'''
pysipp - a python wrapper for launching SIPp
'''
import sys
from os.path import dirname
from load import iter_scen_dirs
import launch
import contextlib
import report


class SIPpFailure(RuntimeError):
    """SIPp commands failed
    """


class plugin(object):
    '''`pluggy` plugin and hook management
    '''
    import pluggy
    import hookspec

    hookimpl = pluggy.HookimplMarker('pysipp')
    mng = pluggy.PluginManager('pysipp', implprefix='pysipp')
    mng.add_hookspecs(hookspec)

    @staticmethod
    @contextlib.contextmanager
    def register(plugins):
        """Temporarily register plugins
        """
        try:
            if any(plugins):
                for p in plugins:
                    plugin.mng.register(p)
            yield
        finally:
            if any(plugins):
                for p in plugins:
                    plugin.mng.unregister(p)


import agent
from agent import client, server

__package__ = 'pysipp'
__author__ = 'Tyler Goodlet (tgoodlet@gmail.com)'

__all__ = ['walk', 'client', 'server', 'plugin']


def walk(rootpath, logdir=None, delay_conf_scen=False):
    """SIPp scenario generator.

    Build and return scenario objects for each scenario directory.
    Most hook calls are described here.
    """
    hooks = plugin.mng.hook
    for path, xmls, confpy in iter_scen_dirs(rootpath):
        # sanity checks
        for xml in xmls:
            assert dirname(xml) == path
        if confpy:
            assert dirname(confpy.__file__) == path

        # predicate hook based filtering
        res = hooks.pysipp_load_scendir(path=path, xmls=xmls, confpy=confpy)
        if res and not all(res):
            continue

        agents = []
        for xml in xmls:
            if 'uac' in xml.lower():
                ua = agent.client(
                    '127.0.0.1', 5060, scen_file=xml, logdir=logdir)
                agents.append(ua)
            elif 'uas' in xml.lower():
                ua = agent.server(scen_file=xml, logdir=logdir)
                agents.insert(0, ua)  # servers are always launched first
            else:
                raise ValueError(
                    "xml script must contain one of 'uac' or 'uas':\n{}"
                    .format(xml)
                )

        # default scen impl
        scen = agent.Scenario(agents, confpy=confpy)

        if not delay_conf_scen:
            scen = hooks.pysipp_conf_scen_protocol(
                agents=scen.agents.values(),
                confpy=confpy
            )

        yield path, scen


def scenario(dirpath=None, logdir=None, proxy=None):
    """Return a single Scenario loaded from `dirpath` if provided else the
    basic default call flow.
    """
    if dirpath:
        # deliver single scenario from dir
        path, scen = next(walk(dirpath))
    else:
        # deliver the default scenario bound to loopback sockets
        uas = agent.server(
            local_host='127.0.0.1', local_port=5060, logdir=logdir)
        uac = agent.client(*uas.sockaddr, logdir=uas.logdir)

        # same as above
        scen = plugin.mng.hook.pysipp_conf_scen_protocol(
            agents=[uas, uac], confpy=None)

        if proxy:
            scen.clients.proxy = proxy

    return scen


# Default hook implementations
@plugin.hookimpl
def pysipp_load_scendir(path, xmls, confpy):
    """If there are no SIPp scripts at the current path then skip this
    directory during collection.
    """
    return bool(xmls)


@plugin.hookimpl
def pysipp_conf_scen_protocol(agents, confpy):
    """Perform default configuration rule set
    """
    # more sanity
    if confpy:
        ua = agents[0]
        assert dirname(confpy.__file__) == dirname(ua.scen_file)

    hooks = plugin.mng.hook
    # register pysipp_conf.py module temporarily so that each scenario only
    # hooks a single pysipp_conf.py
    with plugin.register([confpy]):
        # default scen impl
        scen = agent.Scenario(agents, confpy=confpy)

        # order the agents for launch
        agents = list(hooks.pysipp_order_agents(
            agents=scen.agents, clients=scen.clients,
            servers=scen.servers)) or agents

        # create scenario wrapper
        scen = hooks.pysipp_new_scen(agents=agents, confpy=confpy)

        # configure scenario
        hooks.pysipp_conf_scen(scen=scen)

        # XXX patch pluggy to support direct method parsing allowing to
        # remove ^
        # hooks.pysipp_conf_scen.call_extra(scen=scen)

    return scen


@plugin.hookimpl
def pysipp_order_agents(agents, clients, servers):
    """Lexicographically sort agents by name and always start servers first
    """
    return (agents[name] for name in
            sorted(servers) + sorted(clients))


@plugin.hookimpl
def pysipp_new_scen(agents, confpy):
    return agent.Scenario(agents, confpy=confpy)


@plugin.hookimpl(tryfirst=True)
def pysipp_conf_scen(scen):
    """Default validation logic and routing with media
    """
    # point all clients to send requests to 'primary' server agent
    if scen.servers:
        uas = scen.servers.values()[0]
        scen.clients.remotesockaddr = uas.sockaddr

    elif not scen.clients.proxy:
        # no servers in scenario so point proxy addr to remote socket addr
        for uac in scen.clients.values():
            uac.proxy = uac.remotesockaddr

    # make the non-players echo media
    if scen.has_media and len(scen.agents) == 2:
        for ua in scen.agents.values():
            if not ua.plays_media:
                ua.rtp_echo = True


@plugin.hookimpl
def pysipp_new_runner():
    """Provision and assign a default cmd runner
    """
    return launch.PopenRunner()


@plugin.hookimpl
def pysipp_run_protocol(scen, runner, block, timeout, raise_exc):
    """"Invoked when a scenario object is called.
    """
    # use provided runner or default provided by hook
    runner = runner or plugin.mng.hook.pysipp_new_runner()
    agents = scen.agents.values()

    try:
        # run all agents (raises RuntimeError on timeout)
        cmds2procs = runner(
            (ua.render() for ua in agents),
            block=block, timeout=timeout
        )
    except launch.TimeoutError:  # sucessful timeout
        cmds2procs = runner.get(timeout=0)
        report.emit_logfiles(zip(agents, cmds2procs.values()))
        if raise_exc:
            raise

    # async run
    if not block:
        # XXX async run must bundle up results for later processing
        return runner

    # sync run
    agents2procs = zip(agents, cmds2procs.values())
    msg = report.err_summary(agents2procs)
    if msg:
        # report logs and stderr
        report.emit_logfiles(agents2procs)
        if raise_exc:
            # raise RuntimeError on agent failure(s)
            raise SIPpFailure(msg)

    return runner


# reg default hook set
plugin.mng.register(sys.modules[__name__])
