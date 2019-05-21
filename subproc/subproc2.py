#! env python
# should work with Python 2.7 and 3.x
# subproc.py
from __future__ import print_function

import logging
import os
import shlex
import signal
import subprocess
import threading
from collections import namedtuple
from multiprocessing import TimeoutError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

logger = logging.getLogger(os.path.basename(__file__.replace('.py', '')))

RunResult = namedtuple('RunResult', ['pid', 'return_code', 'stdout', 'stderr'])
RedirectedRunResult = namedtuple('RedirectedRunResult', ['pid', 'return_code'])


def run(cmd, timeoutsec=None, formatter=None):
    """\
    Executes the given command and captures its stdout and stderr output.

    By default, the resulting process and all its child processes are grouped together in a process group.
    In case of a timeout, the process and its child processes are terminated.

    :param cmd: the command to execute
    :param timeoutsec: interrupts the process after the timeout (in seconds)
    :param formatter: function accepting and returning the line to print
    :return: :py:class:`RunResult`

    Example::

        r = run('echo hello world', formatter=str.upper)
        assert r.stdout == 'HELLO WORLD'
    """
    out = StringIO()
    err = StringIO()
    result = run_redirected(cmd, out=out, err=err, timeoutsec=timeoutsec, formatter=formatter)
    return RunResult(result.pid, result.return_code, out.getvalue(), err.getvalue())


def run_redirected(cmd, out=None, err=None, timeoutsec=None, formatter=None):
    """\
    Executes the given command and redirects its output if applicable.

    By default, the resulting process and all its child processes are grouped together in a process group.
    In case of a timeout, the process and its child processes are terminated.

    :param cmd: the command to execute
    :param out: file-like object to write the stdout to (default sys.stdout)
    :param err: file-like object to write the stderr to (default sys.stderr)
    :param timeoutsec: interrupts the process after the timeout (in seconds)
    :param formatter: function accepting and returning the line to print
    :return: :py:class:`RedirectedRunResult`

    Example::

        with open('proc.log', 'w') as f:
            r = run_to_file('echo hello world', out=f, formatter=str.upper)
            assert r.return_code == 0
    """

    def write(input, output):
        logging.debug('Thread started to read from pipe')
        for line in iter(input.readline, ''):
            formatted_line = formatter(line) if formatter else line
            output.write(formatted_line)
        logging.debug('Thread stopped')

    def close_pipes():
        if not p:
            return
        if out:
            p.stdout.close()
        if err:
            p.stderr.close()

    p = None
    try:
        p = subprocess.Popen(shlex.split(cmd), **(process_params(out, err)))
    # catch errors when creating process (e.g. if command was not found)
    except OSError as e:
        # prevents deadlocks
        logging.error('Closing pipes due to unexpected error: %s', e)
        close_pipes()
        raise e

    try:
        # start consuming pipes
        threads = []
        if out or formatter:
            t = threading.Thread(target=write, args=(p.stdout, out))
            t.daemon = True
            threads.append(t)
        if err or formatter:
            t = threading.Thread(target=write, args=(p.stderr, err))
            t.daemon = True
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=timeoutsec)
        if any((t.is_alive() for t in threads)):
            raise TimeoutError
    except TimeoutError as e:
        logging.warn('Terminating process due to timeout')
        if os.name == 'posix':
            os.killpg(p.pid, signal.SIGTERM)
        elif os.name == 'nt':
            os.kill(p.pid, signal.CTRL_C_EVENT)
        raise e

    # pull return code
    p.wait()

    return RedirectedRunResult(p.pid, p.returncode)


def process_params(out, err):
    params = {
        'universal_newlines': True,
    }
    # make progress group leader so that signals are directed its children as well
    if os.name == 'posix':
        params['preexec_fn'] = os.setpgrp
    elif os.name == 'nt':
        params['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    # notice that the pipes needs to be consumed
    # otherwise this python process will block
    # when the pipe reaches its capacity limit (on linux 16 pages = 65,536 bytes)
    if out:
        logging.debug('Setting up pipe for STDOUT')
        params['stdout'] = subprocess.PIPE
    if err:
        logging.debug('Setting up pipe for STDERR')
        params['stderr'] = subprocess.PIPE
    return params
