import pysipp


@pysipp.plugin.hookimpl
def pysipp_conf_scen(scen):
    scen.agents.remote_host = 'doggy'


@pysipp.plugin.hookimpl
def pysipp_order_agents(agentsdict, clientsdict, serversdict):
    return reversed(agentsdict.values())
