"""
Launchers for invoking SIPp user agents
"""
import shlex
import signal
import subprocess
import time
from . import utils
from collections import OrderedDict, namedtuple
from functools import partial
from pprint import pformat

import trio

from . import report

log = utils.get_logger()

Streams = namedtuple("Streams", "stdout stderr")


class TimeoutError(Exception):
    "SIPp process timeout exception"


class SIPpFailure(RuntimeError):
    """SIPp commands failed"""


class TrioRunner(object):
    """Run a sequence of SIPp cmds asynchronously. If any process terminates
    with a non-zero exit code, immediately canacel all remaining processes and
    collect std streams.
    """

    def __init__(
        self,
    ):
        # store proc results
        self._procs = OrderedDict()

    async def run(self, cmds, rate=300, **kwargs):
        if self.is_alive():
            raise RuntimeError("Not all processes from a prior run have completed")
        if self._procs:
            raise RuntimeError(
                "Process results have not been cleared from previous run"
            )
        # run agent commands in sequence
        for cmd in cmds:
            log.debug('launching cmd:\n"{}"\n'.format(cmd))
            proc = await trio.open_process(
                shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            self._procs[cmd] = proc

            # limit launch rate
            time.sleep(1.0 / rate)

        return self._procs

    async def get(self, timeout=180):
        """Block up to `timeout` seconds for all agents to complete.
        Either return (cmd, proc) pairs or raise `TimeoutError` on timeout
        """
        signalled = None

        # taken mostly verbatim from ``trio.run_process()``
        async def read_output(stream):
            chunks = []
            async with stream:
                try:
                    while True:
                        chunk = await stream.receive_some(32768)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except trio.ClosedResourceError:
                    pass

                return b"".join(chunks)

        async def wait_on_proc(proc):
            nonlocal signalled
            async with proc as proc:
                rc = await proc.wait()
                if rc != 0 and not signalled:
                    # stop all other agents if there is a failure
                    signalled = self.stop()

                # collect stderr output
                proc.stderr_output = await read_output(proc.stderr)

        try:
            with trio.fail_after(timeout):
                async with trio.open_nursery() as n:
                    for cmd, proc in self._procs.items():
                        # async wait on each process to complete
                        n.start_soon(wait_on_proc, proc)

                return self._procs

        except trio.TooSlowError:
            # kill all SIPp processes
            signalled = self.stop()
            # all procs were killed by SIGUSR1
            raise TimeoutError(
                "pids '{}' failed to complete after '{}' seconds".format(
                    pformat([p.pid for p in signalled.values()]), timeout
                )
            )

    def iterprocs(self):
        """Iterate all processes which are still alive yielding
        (cmd, proc) pairs
        """
        return (
            (cmd, proc)
            for cmd, proc in self._procs.items()
            if proc and proc.poll() is None
        )

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
            log.warn(
                "sent signal '{}' to cmd '{}' with pid '{}'".format(
                    signum, cmd, proc.pid
                )
            )
            signalled[cmd] = proc
        return signalled

    def is_alive(self):
        """Return bool indicating whether some agents are still alive"""
        return any(self.iterprocs())

    def clear(self):
        """Clear all processes from the last run"""
        assert not self.is_alive(), "Not all processes have completed"
        self._procs.clear()


async def run_all_agents(runner, agents, timeout, block=True):
    """Run a sequencec of agents using a ``TrioRunner``."""

    try:
        await runner.run((ua.render() for ua in agents), timeout=timeout)
        if block:
            return await finalize(runner, agents, timeout)
        else:
            return finalizer(finalize, runner, agents)
    except TimeoutError as terr:
        # print error logs even when we timeout
        try:
            return await finalize(runner, agents, timeout)
        except SIPpFailure as err:
            assert "exit code -9" in str(err)
            raise terr


async def finalize(runner, agents, timeout):
    """Block up to `timeout` seconds for all agents to complete."""
    # this might raise TimeoutError
    cmds2procs = await runner.get(timeout=timeout)
    agents2procs = list(zip(agents, cmds2procs.values()))
    msg = report.err_summary(agents2procs)
    if msg:
        # report logs and stderr
        await report.emit_logfiles(agents2procs)
        raise SIPpFailure(msg)

    return cmds2procs


def finalizer(finalize_coro, runner, agents):
    def with_timeout(timeout):
        return trio.run(
            partial(finalize_coro, timeout=timeout),
            runner,
            agents,
        )

    return with_timeout
