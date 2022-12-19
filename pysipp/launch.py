"""
Launchers for invoking SIPp user agents
"""
import os
import select
import shlex
import signal
import subprocess
import threading
import time
from collections import namedtuple
from collections import OrderedDict
from pprint import pformat

from . import utils

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
        subprocmod=subprocess,
        osmod=os,
        poller=select.epoll,
    ):
        # these could optionally be rpyc proxy objs
        self.spm = subprocmod
        self.osm = osmod
        self.poller = poller()
        # collector thread placeholder
        self._waiter = None
        # store proc results
        self._procs = OrderedDict()

    def __call__(self, cmds, block=True, rate=300, **kwargs):
        if self._waiter and self._waiter.is_alive():
            raise RuntimeError(
                "Not all processes from a prior run have completed"
            )
        if self._procs:
            raise RuntimeError(
                "Process results have not been cleared from previous run"
            )
        sp = self.spm
        os = self.osm
        DEVNULL = open(os.devnull, "wb")
        fds2procs = OrderedDict()

        # run agent commands in sequence
        for cmd in cmds:
            log.debug('launching cmd:\n"{}"\n'.format(cmd))
            proc = sp.Popen(shlex.split(cmd), stdout=DEVNULL, stderr=sp.PIPE)
            fd = proc.stderr.fileno()
            log.debug("registering fd '{}' for pid '{}'".format(fd, proc.pid))
            fds2procs[fd] = self._procs[cmd] = proc
            # register for stderr hangup events
            self.poller.register(proc.stderr.fileno(), select.EPOLLHUP)
            # limit launch rate
            time.sleep(1.0 / rate)

        # launch waiter
        self._waiter = threading.Thread(target=self._wait, args=(fds2procs,))
        self._waiter.daemon = True
        self._waiter.start()

        return self.get(**kwargs) if block else self._procs

    def _wait(self, fds2procs):
        log.debug("started waiter for procs {}".format(fds2procs))
        signalled = None
        left = len(fds2procs)
        collected = 0
        while collected < left:
            pairs = self.poller.poll()  # wait on hangup events
            log.debug("received hangup for pairs '{}'".format(pairs))
            for fd, status in pairs:
                collected += 1
                proc = fds2procs[fd]
                # attach streams so they can be read more then once
                log.debug("collecting streams for {}".format(proc))
                proc.streams = Streams(*proc.communicate())  # timeout=2))
                if proc.returncode != 0 and not signalled:
                    # stop all other agents if there is a failure
                    signalled = self.stop()

        log.debug("terminating waiter thread")

    def get(self, timeout=180):
        """Block up to `timeout` seconds for all agents to complete.
        Either return (cmd, proc) pairs or raise `TimeoutError` on timeout
        """
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
                        # some procs failed to terminate via signalling
                        raise RuntimeError("Unable to kill all agents!?")

                # all procs were killed by SIGUSR1
                raise TimeoutError(
                    "pids '{}' failed to complete after '{}' seconds".format(
                        pformat([p.pid for p in signalled.values()]), timeout
                    )
                )

        return self._procs

    def stop(self):
        """Stop all agents with SIGUSR1 as per SIPp's signal handling"""
        return self._signalall(signal.SIGUSR1)

    def terminate(self):
        """Kill all agents with SIGTERM"""
        return self._signalall(signal.SIGTERM)

    def _signalall(self, signum):
        signalled = OrderedDict()
        for cmd, proc in self.iterprocs():
            proc.send_signal(signum)
            log.warning(
                "sent signal '{}' to cmd '{}' with pid '{}'".format(
                    signum, cmd, proc.pid
                )
            )
            signalled[cmd] = proc
        return signalled

    def iterprocs(self):
        """Iterate all processes which are still alive yielding
        (cmd, proc) pairs
        """
        return (
            (cmd, proc)
            for cmd, proc in self._procs.items()
            if proc and proc.poll() is None
        )

    def is_alive(self):
        """Return bool indicating whether some agents are still alive"""
        return any(self.iterprocs())

    def ready(self):
        """Return bool indicating whether all agents have completed"""
        return not self.is_alive()

    def clear(self):
        """Clear all processes from the last run"""
        assert self.ready(), "Not all processes have completed"
        self._procs.clear()
