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
"""
pysipp - a python wrapper for launching SIPp
"""
import sys
from os.path import dirname
from . import plugin, netplug, agent
from .load import iter_scen_dirs
from .agent import client, server


__package__ = "pysipp"
__author__ = "Tyler Goodlet (tgoodlet@gmail.com)"

__all__ = ["walk", "client", "server", "plugin"]


def walk(rootpath, delay_conf_scen=False, autolocalsocks=True, **scenkwargs):
    """SIPp scenario generator.

    Build and return scenario objects for each scenario directory.
    Most hook calls are described here.
    """
    with plugin.register([netplug] if autolocalsocks else []):
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
                if "uac" in xml.lower():
                    ua = agent.client(scen_file=xml)
                    agents.append(ua)
                elif "uas" in xml.lower():
                    ua = agent.server(scen_file=xml)
                    agents.insert(0, ua)  # servers are always launched first
                else:
                    raise ValueError(
                        "xml script must contain one of 'uac' or 'uas':\n{}".format(xml)
                    )

            if delay_conf_scen:
                # default scen impl
                scen = agent.Scenario(agents, confpy=confpy)

            else:
                scen = hooks.pysipp_conf_scen_protocol(
                    agents=agents,
                    confpy=confpy,
                    scenkwargs=scenkwargs,
                )

            yield path, scen


def scenario(dirpath=None, proxyaddr=None, autolocalsocks=True, **scenkwargs):
    """Return a single Scenario loaded from `dirpath` if provided else the
    basic default call flow.
    """
    if dirpath:
        # deliver single scenario from dir
        path, scen = next(walk(dirpath, autolocalsocks=autolocalsocks, **scenkwargs))
    else:
        with plugin.register([netplug] if autolocalsocks else []):
            # deliver the default scenario bound to loopback sockets
            uas = agent.server()
            uac = agent.client()

            # same as above
            scen = plugin.mng.hook.pysipp_conf_scen_protocol(
                agents=[uas, uac],
                confpy=None,
                scenkwargs=scenkwargs,
            )

    if proxyaddr is not None:
        assert isinstance(proxyaddr, tuple), "proxyaddr must be a (addr, port) tuple"
        scen.clientdefaults.proxyaddr = proxyaddr

    return scen


# Default hook implementations
@plugin.hookimpl
def pysipp_load_scendir(path, xmls, confpy):
    """If there are no SIPp scripts at the current path then skip this
    directory during collection.
    """
    return bool(xmls)


@plugin.hookimpl
def pysipp_conf_scen_protocol(agents, confpy, scenkwargs):
    """Perform default configuration rule set"""
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
        agents = (
            list(
                hooks.pysipp_order_agents(
                    agents=scen.agents, clients=scen.clients, servers=scen.servers
                )
            )
            or agents
        )

        # create scenario wrapper
        scen = hooks.pysipp_new_scen(
            agents=agents, confpy=confpy, scenkwargs=scenkwargs
        )

        # configure scenario
        hooks.pysipp_conf_scen(agents=scen.agents, scen=scen)

        # XXX patch pluggy to support direct method parsing allowing to
        # remove ^
        # hooks.pysipp_conf_scen.call_extra(scen=scen)

    return scen


@plugin.hookimpl
def pysipp_order_agents(agents, clients, servers):
    """Lexicographically sort agents by name and always start servers first"""
    return (agents[name] for name in sorted(servers) + sorted(clients))


@plugin.hookimpl
def pysipp_new_scen(agents, confpy, scenkwargs):
    return agent.Scenario(agents, confpy=confpy, **scenkwargs)


@plugin.hookimpl(trylast=True)
def pysipp_conf_scen(agents, scen):
    """Default validation logic and routing with media"""
    if scen.servers:
        # point all clients to send requests to 'primary' server agent
        # if they aren't already
        servers_addr = scen.serverdefaults.get("srcaddr", ("127.0.0.1", 5060))
        uas = scen.prepare_agent(list(scen.servers.values())[0])
        scen.clientdefaults.setdefault("destaddr", uas.srcaddr or servers_addr)

    elif not scen.clientdefaults.proxyaddr:
        # no servers in scenario so point proxy addr to remote socket addr
        scen.clientdefaults.proxyaddr = scen.clientdefaults.destaddr

    # make the non-players echo media
    if scen.has_media and len(scen.agents) == 2:
        for ua in scen.agents.values():
            if not ua.plays_media:
                ua.rtp_echo = True


# register the default hook set
plugin.mng.register(sys.modules[__name__])
