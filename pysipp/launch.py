"""
Launchers for invoking SIPp user agents
"""
import os
import subprocess
import shlex
import select
import threading
import logging
import signal
from collections import OrderedDict, namedtuple

log = logging.getLogger(__name__)


Streams = namedtuple("Streams", "stdout stderr")


class PopenRunner(object):
    """Run a sequence of SIPp agents asynchronously. If any process terminates
    with a non-zero exit code, immediately kill all remaining processes and
    collect std streams.

    Adheres to an interface similar to `multiprocessing.pool.AsyncResult`.
    """
    class TimeoutError(Exception):
        pass

    def __init__(self, agents, subprocmod=subprocess, poller=select.epoll()):
        self.agents = OrderedDict.fromkeys(agents)
        self.spm = subprocmod  # this could optionally be an rpyc proxy obj
        self.poller = poller
        self.procs = OrderedDict()
        # collector thread placeholder
        self._waiter = None

    def __call__(self, block=True, **kwargs):
        if self._waiter and self._waiter.is_alive():
            raise RuntimeError(
                "Not all processes from previous run have completed"
            )
        else:
            self._waiter = threading.Thread(target=self._wait)  # ,daemon=True)
            self._waiter.start()

        sp = self.spm
        # run agent commands in sequence
        for agent in self.agents:
            proc = sp.Popen(
                shlex.split(agent.render()),
                stdout=sp.PIPE,
                stderr=sp.PIPE
            )
            self.procs[proc.stdout.fileno()] = self.agents[agent] = proc
            # register for stdout hangup events
            self.poller.register(proc.stdout.fileno(), select.EPOLLHUP)

        return self.get() if block else None

    def _wait(self):
        signalled = None
        left = len(self.agents)
        for _ in range(left):
            # fd, status = self.poller.poll()  # wait on stdout hangup events
            pairs = self.poller.poll()  # wait on stdout hangup events
            for fd, status in pairs:
                proc = self.procs[fd]
                # attach streams so they can be read more then once
                proc.streams = Streams(*proc.communicate(timeout=2))
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
                    self.terminate()
                    self._waiter.join(timeout=10)
                    if self._waiter.is_alive():
                        raise RuntimeError("Unable to kill all agents!?")

                # all procs were killed by SIGUSR1
                raise TimeoutError("Agents '{}' failed to complete after '{}' seconds"
                                   .format(signalled, timeout))
        return self.agents.items()

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
            log.debug("sent '{}' to agent '{}' with pid '{}'"
                      .format(signal, agent, proc.pid))
            if proc.poll() is not None:
                signalled[agent] = proc
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
