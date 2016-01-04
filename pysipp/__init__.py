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
from load import iter_scen_dirs
from launch import PopenRunner


class plugin(object):
    '''`pluggy` plugin and hook management
    '''
    import pluggy
    import hookspec

    hookimpl = pluggy.HookimplMarker('pysipp')
    mng = pluggy.PluginManager('pysipp')
    mng.add_hookspecs(hookspec)


import agent

__package__ = 'pysipp'
__author__ = 'Tyler Goodlet (tgoodlet@gmail.com)'

__all__ = ['walk', 'client', 'server', 'plugin']


def walk(rootpath, logdir=None):
    """SIPp scenario generator.

    Build and return scenario objects for each scenario directory.
    Most hook calls are described here.
    """
    hooks = plugin.mng.hook
    for path, xmls, confpy in iter_scen_dirs(rootpath):

        # predicate hook based filtering
        res = hooks.pysipp_load_scendir(path=path, xmls=xmls, confpy=confpy)
        if res and not all(res):
            continue

        agents = []
        for xml in xmls:
            if 'uac' in xml:
                ua = agent.client(
                    '127.0.0.1', 5060, scen_file=xml, logdir=logdir)
                agents.append(ua)
            elif 'uas' in xml:
                ua = agent.server(scen_file=xml, logdir=logdir)
                agents.insert(0, ua)  # servers are always launched first
            else:
                raise ValueError(
                    "xml script must contain one of 'uac' or 'uas':\n{}"
                    .format(xml)
                )

        # get agents launch order
        scen = agent.Scenario(agents)

        # register conf.py module only during init so that each scenario only
        # hooks it once
        if confpy:
            plugin.mng.register(confpy)

        agents = hooks.pysipp_order_agents(
            agentsdict=scen.agents, clientsdict=scen.clients,
            serversdict=scen.servers) or agents

        # create scenario wrapper
        scen = hooks.pysipp_new_scen(agents=agents, confpy=confpy)

        # configure scenario
        plugin.mng.hook.pysipp_conf_scen(scen=scen)

        # XXX patch pluggy to support direct method parsing allowing to remover
        # plugin.mng.hook.pysipp_conf_scen.call_extra(scen=scen)

        # create and attach a default runner
        scen.runner = plugin.mng.hook.pysipp_new_runner(scen=scen)

        if confpy:
            plugin.mng.unregister(confpy)

        yield path, scen


# Default hook implementations
@plugin.hookimpl
def pysipp_load_scendir(path, xmls, confpy):
    """If there are no SIPp scripts at the current path then skip this
    directory during collection.
    """
    return bool(xmls)


@plugin.hookimpl
def pysipp_order_agents(agentsdict, clientsdict, serversdict):
    """Lexicographically sort agents by name and always start servers first
    """
    return (agentsdict[name] for name in
            sorted(serversdict) + sorted(clientsdict))


@plugin.hookimpl
def pysipp_new_scen(agents, confpy):
    return agent.Scenario(agents, confpy=confpy)


@plugin.hookimpl(tryfirst=True)
def pysipp_conf_scen(scen):
    """Default validation logic and routing to ensure a successful run
    """
    pass


@plugin.hookimpl
def pysipp_new_runner(scen):
    """Provision a default cmd runner
    """
    return PopenRunner(scen.agents.values())


@plugin.hookimpl
def pysipp_run_protocol(scen, runner, block, timeout):
    """"Invoked when a scenario object is called.
    """
    # use provided runner or default provided by hook
    runner = runner or scen.runner
    scen.runner = runner
    # run scenario
    return runner(block=block, timeout=timeout)


# reg default hook set
plugin.mng.register(sys.modules[__name__])
