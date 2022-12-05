"""
auto-networking plugin
"""
import socket

from pysipp import plugin


def getsockaddr(host, family=socket.AF_INET, port=0, sockmod=socket):
    """Retrieve a random socket address from the local OS by
    binding to an ip, acquiring a random port and then
    closing the socket and returning that address.

    ..warning:: Obviously this is not guarateed to be an unused address
        since we don't actually keep it bound, so there may be a race with
        other processes acquiring the addr before our SIPp process re-binds.
    """
    for fam, stype, proto, _, sa in socket.getaddrinfo(
        host,
        port,
        family,
        socket.SOCK_DGRAM,
        0,
        socket.AI_PASSIVE,
    ):
        s = socket.socket(family, stype, proto)
        s.bind(sa)
        sockaddr = s.getsockname()[:2]
        s.close()
        return sockaddr

    raise socket.error("getaddrinfo returned empty sequence")


@plugin.hookimpl
def pysipp_conf_scen(agents, scen):
    """Automatically allocate random socket addresses from the local OS for
    each agent in the scenario if not previously set by the user.
    """
    host = scen.defaults.local_host or socket.getfqdn()
    for ua in scen.agents.values():
        copy = scen.prepare_agent(ua)

        ip, port = getsockaddr(ua.local_host or host)

        if not copy.local_host:
            ua.local_host = ip

        if not copy.local_port:
            ua.local_port = port

        if not copy.media_addr:
            ua.media_addr = ua.local_host

        if not copy.media_port:
            ua.media_port = getsockaddr(ua.media_addr or host)[1]
