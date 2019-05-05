#! env python
# should work with Python 2.7 and 3.x
# subproc.py
from __future__ import print_function

import logging
import os
import shlex
import signal
import subprocess
import sys
from contextlib import contextmanager
from multiprocessing import TimeoutError

logger = logging.getLogger(os.path.basename(__file__.replace('.py', '')))


@contextmanager
def timeout(timeoutsec):
    def raise_timeout(signum, frame):
        raise TimeoutError

    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(timeoutsec)
    try:
        yield
    finally:
        # Unregister the signal
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def pipe_processes(cmds):
    processes = []
    try:
        cmd = "".join(cmds[-1:])
        params = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'universal_newlines': True,
            'preexec_fn': os.setsid,  # create process group to kill child processes as well
        }
        if cmds[:-1]:
            processes = list(pipe_processes(cmds[:-1]))
            logger.debug("Running cmd {}: {}".format(len(cmds), cmd))
            processes.append(subprocess.Popen(shlex.split(cmd), stdin=processes[-1].stdout, **params))
        else:
            logger.debug("Running cmd {}: {}".format(len(cmds), cmd))
            processes.append(subprocess.Popen(shlex.split(cmd), **params))
        return processes
    # catch errors when creating process (e.g. if command was not found)
    except OSError as e:
        logger.error("Running last cmd failed: {}".format(str(e)))
        for p in processes:
            p.stdout.close()  # close pipe to prevent dead locks
        raise e


def run(cmds, writer=sys.stdout.write, timeoutsec=-1):
    _cmds = (cmds,) if isinstance(cmds, str) else cmds
    _cmds = tuple(filter(lambda cmd: bool(cmd), _cmds))
    if not _cmds:
        return tuple()

    processes = pipe_processes(_cmds)
    try:
        with timeout(timeoutsec):
            for line in iter(processes[-1].stdout.readline, ''):
                writer(line)
    except TimeoutError as e:
        logger.warning("Commands didn't end in time. Killing...")
        for p in processes:
            os.killpg(p.pid, signal.SIGTERM)
        raise e
    finally:
        logger.debug("Closing pipes...")
        for p in processes:
            # close pipe otherwise we might run into a dead lock, e.g.
            # when a pipe consuming process stops reading (BrokenPipeError)
            p.stdout.close()
            p.wait()  # poll does not work since it returns false positives
    result = tuple(zip(_cmds, [p.returncode for p in processes]))
    if any([status_code != 0 for _, status_code in result]):
        logger.warning("Some commands didn't return successfully")
    return result
