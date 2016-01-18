"""
Launchers for invoking SIPp user agents
"""
import subprocess
import os
import shlex
import select
import threading
import utils
import signal
import time
from collections import OrderedDict, namedtuple

log = utils.get_logger()

Streams = namedtuple("Streams", "stdout stderr")


class TimeoutError(Exception):
    "SIPp process timeout exception"


class PopenRunner(object):
    """Run a sequence of SIPp agents asynchronously. If any process terminates
    with a non-zero exit code, immediately kill all remaining processes and
    collect std streams.

    Adheres to an interface similar to `multiprocessing.pool.AsyncResult`.
    """
    def __init__(
        self,
        agents,
        subprocmod=subprocess,
        osmod=os,
        poller=select.epoll,
    ):
        self.agents = OrderedDict.fromkeys(agents)
        # these could optionally be rpyc proxy objs
        self.spm = subprocmod
        self.osm = osmod
        self.poller = poller()
        self.procs = OrderedDict()
        # collector thread placeholder
        self._waiter = None

    def __call__(self, block=True, rate=300, **kwargs):
        if self._waiter and self._waiter.is_alive():
            raise RuntimeError(
                "Not all processes from previous run have completed"
            )
        sp = self.spm
        os = self.osm
        DEVNULL = open(os.devnull, 'wb')

        # run agent commands in sequence
        for agent in self.agents:
            cmd = agent.render()
            log.debug(
                "launching agent '{}' cmd:\n\"{}\"\n".format(agent.name, cmd))
            proc = sp.Popen(
                shlex.split(agent.render()),
                stdout=DEVNULL,
                stderr=sp.PIPE
            )
            fd = proc.stderr.fileno()
            log.debug("registering fd '{}' for pid '{}'".format(
                fd, proc.pid))
            self.procs[fd] = self.agents[agent] = proc
            # register for stderr hangup events
            self.poller.register(proc.stderr.fileno(), select.EPOLLHUP)
            # limit launch rate
            time.sleep(1. / rate)

        # launch waiter
        self._waiter = threading.Thread(target=self._wait)
        self._waiter.daemon = True
        self._waiter.start()

        return self.get(**kwargs) if block else None

    def _wait(self):
        log.debug("started waiter for procs {}".format(self.procs))
        signalled = None
        left = len(self.agents)
        collected = 0
        while collected < left:
            pairs = self.poller.poll()  # wait on hangup events
            log.debug("received hangup for pairs '{}'".format(pairs))
            for fd, status in pairs:
                collected += 1
                proc = self.procs[fd]
                # attach streams so they can be read more then once
                log.debug("collecting streams for {}".format(proc))
                proc.streams = Streams(*proc.communicate())  # timeout=2))
                if proc.returncode != 0 and not signalled:
                    # stop all other agents if there is a failure
                    signalled = self.stop()

        log.debug("terminating waiter thread")

    def get(self, timeout=180):
        '''Block up to `timeout` seconds for all agents to complete.
        Either return (agent, proc) pairs or raise `TimeoutError` on timeout
        '''
        if self._waiter.is_alive():
            self._waiter.join(timeout=timeout)
            if self._waiter.is_alive():
                # kill them mfin SIPps
                signalled = self.stop()
                self._waiter.join(timeout=10)
                if self._waiter.is_alive():
                    # try to stop a few more times
                    for _ in range(3):
                        signalled = self.stop()
                        self._waiter.join(timeout=1)
                    if self._waiter.is_alive():
                        raise TimeoutError("Unable to kill all agents!?")

                # all procs were killed by SIGUSR1
                raise RuntimeError(
                    "Agents '{}' failed to complete after '{}' seconds"
                    .format(signalled, timeout)
                )
        return self.agents

    def stop(self):
        '''Stop all agents with SIGUSR1 as per SIPp's signal handling
        '''
        return self._signalall(signal.SIGUSR1)

    def terminate(self):
        '''Kill all agents with SIGTERM
        '''
        return self._signalall(signal.SIGTERM)

    def _signalall(self, signum):
        signalled = OrderedDict()
        for agent, proc in self.iterprocs():
            proc.send_signal(signum)
            log.debug("sent signal '{}' to agent '{}' with pid '{}'"
                      .format(signum, agent, proc.pid))
            signalled[agent.name] = proc
        return signalled

    def iterprocs(self):
        '''Iterate all processes which are still alive yielding
        (agent, proc) pairs
        '''
        return ((agent, proc) for agent, proc in self.agents.items()
                if proc and proc.poll() is None)

    def is_alive(self):
        '''Return bool indicating whether some agents are still alive
        '''
        return any(self.iterprocs())

    def ready(self):
        '''Return bool indicating whether all agents have completed
        '''
        return not self.is_alive()

    def clear(self):
        '''Clear all processes from the last run
        '''
        assert self.ready(), "Not all processes have completed"
        self.agents.clear()
