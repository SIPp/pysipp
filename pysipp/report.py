"""
reporting for writing SIPp log files to the console
"""
import time
from collections import OrderedDict
from os import path

from . import utils

log = utils.get_logger()

EXITCODES = {
    0: "All calls were successful",
    1: "At least one call failed",
    15: "Process was terminated",
    97: "Exit on internal command. Calls may have been processed",
    99: "Normal exit without calls processed",
    -1: "Fatal error",
    -2: "Fatal error binding a socket",
    -10: "Signalled to stop with SIGUSR1",
    254: "Connection Error: socket already in use",
    255: "Command or syntax error: check stderr output",
}


def err_summary(agents2procs):
    """Return an error message detailing SIPp cmd exit codes
    if any of the commands exitted with a non-zero status
    """
    name2ec = OrderedDict()
    # gather all exit codes
    for ua, proc in agents2procs:
        name2ec[ua.name] = proc.returncode

    if any(name2ec.values()):
        # raise a detailed error
        msg = "Some agents failed\n"
        msg += "\n".join(
            "'{}' with exit code {} -> {}".format(
                name, rc, EXITCODES.get(rc, "unknown exit code")
            )
            for name, rc in name2ec.items()
        )
        return msg


def emit_logfiles(agents2procs, level="warning", max_lines=100):
    """Log all available SIPp log-file contents"""
    emit = getattr(log, level)
    for ua, proc in agents2procs:

        # print stderr
        emit(
            "stderr for '{}' @ {}\n{}\n".format(
                ua.name, ua.srcaddr, proc.streams.stderr
            )
        )
        # FIXME: no idea, but some logs are not being printed without this
        # logging mod bug?
        time.sleep(0.01)

        # print log file contents
        for name, fpath in ua.iter_toconsole_items():
            if fpath and path.isfile(fpath):
                with open(fpath, "r") as lf:
                    lines = lf.readlines()
                    llen = len(lines)

                    # truncate long log files
                    if llen > max_lines:
                        toolong = (
                            "...\nOutput has been truncated to {} lines - "
                            "see '{}' for full details\n"
                        ).format(max_lines, fpath)
                        output = "".join(lines[:max_lines]) + toolong
                    else:
                        output = "".join(lines)
                    # log it
                    emit(
                        "'{}' contents for '{}' @ {}:\n{}".format(
                            name, ua.name, ua.srcaddr, output
                        )
                    )
                    # FIXME: same as above
                    time.sleep(0.01)
