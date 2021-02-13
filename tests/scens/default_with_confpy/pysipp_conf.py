def pysipp_conf_scen(agents, scen):
    scen.uri_username = "doggy"
    agents["uac"].srcaddr = "127.0.0.1", 5070


def pysipp_order_agents(agents, clients, servers):
    # should still work due to re-transmissions
    return reversed(list(agents.values()))
