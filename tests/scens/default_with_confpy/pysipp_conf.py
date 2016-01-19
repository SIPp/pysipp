def pysipp_conf_scen(scen):
    scen.agents.remote_host = 'doggy'


def pysipp_order_agents(agents, clients, servers):
    return reversed(agents.values())
