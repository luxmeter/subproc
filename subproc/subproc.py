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
    from itertools import izip
except ImportError:
    izip = zip


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

logger = logging.getLogger(os.path.basename(__file__.replace('.py', '')))

RunResult = namedtuple('RunResult', ['pid', 'return_code', 'stdout', 'stderr'])
RunRedirectedResult = namedtuple('RunRedirectedResult', ['pid', 'return_code'])

Info = namedtuple('Pid', ['cmd', 'pid', 'return_code'])
RunCmdsResult = namedtuple('RunCmdsResult', ['infos', 'stdout', 'stderr'])
RunCmdsRedirectedResult = namedtuple('RunCmdsRedirectedResult', ['info'])


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
    :return: :py:class:`RunRedirectedResult`

    Example::

        with open('proc.log', 'w') as f:
            r = run_to_file('echo hello world', out=f, formatter=str.upper)
            assert r.return_code == 0
    """

    p = pipe_processes([cmd], out, err)[0]
    consume_pipes([p], out, err, timeoutsec, formatter)

    # pull return code
    p.wait()

    return RunRedirectedResult(p.pid, p.returncode)


def run_cmds(cmds, timeoutsec=None, formatter=None):
    """\
    Executes the given commands by piping them together.
    Stdout as well as stderr are captured.

    By default, the resulting processes and all its child processes are grouped together in a process group.
    In case of a timeout, the processes and its child processes are terminated.

    :param cmds: the commands to execute
    :param out: file-like object to write the stdout to (default sys.stdout)
    :param err: file-like object to write the stderr to (default sys.stderr)
    :param timeoutsec: interrupts the processes after the timeout (in seconds)
    :param formatter: function accepting and returning the line to print
    :return: :py:class:`RunCmdsRedirected`

    Example::

        with open('proc.log', 'w') as f:
            r = run_cmds_redirected(['echo hello world', 'sed s/hello/bye/g'], out=f, formatter=str.upper)
            assert r.return_code == 0
    """
    out = StringIO()
    err = StringIO()
    results = run_cmds_redirected(cmds, out=out, err=err, timeoutsec=timeoutsec, formatter=formatter)
    return RunCmdsResult([r.info for r in results], out.getvalue(), err.getvalue())


def run_cmds_redirected(cmds, out=None, err=None, timeoutsec=None, formatter=None):
    """\
    Executes the given commands by piping them together.
    Output is redirected if applicable.

    By default, the resulting processes and all its child processes are grouped together in a process group.
    In case of a timeout, the processes and its child processes are terminated.

    :param cmds: the commands to execute
    :param out: file-like object to write the stdout to (default sys.stdout)
    :param err: file-like object to write the stderr to (default sys.stderr)
    :param timeoutsec: interrupts the processes after the timeout (in seconds)
    :param formatter: function accepting and returning the line to print
    :return: :py:class:`RunCmdsRedirected`

    Example::

        with open('proc.log', 'w') as f:
            r = run_cmds_redirected(['echo hello world', 'sed s/hello/bye/g'], out=f, formatter=str.upper)
            assert r.return_code == 0
    """
    if not cmds:
        return ValueError('No commands defined')

    processes = pipe_processes(cmds, out, err)
    consume_pipes(processes, out, err, timeoutsec, formatter)

    # pull return code
    for p in processes:
        # close pipe otherwise we might run into a dead lock, e.g.
        # when a pipe consuming process stops reading (BrokenPipeError)
        close_pipes(p, out, err)
        p.wait()

    return [RunCmdsRedirectedResult(info=Info(cmd, p.pid, p.returncode)) for cmd, p in izip(cmds, processes)]


def consume_pipes(processes, out, err, timeoutsec, formatter):
    def write(input, output):
        logging.debug('Thread started to read from pipe')
        for line in iter(input.readline, ''):
            formatted_line = formatter(line) if formatter else line
            output.write(formatted_line)
        logging.debug('Thread stopped')

    p = processes[-1]
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
        for p in processes:
            if os.name == 'posix':
                os.killpg(p.pid, signal.SIGTERM)
            elif os.name == 'nt':
                os.kill(p.pid, signal.CTRL_C_EVENT)


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


def close_pipes(p, out, err):
    if not p:
        return
    if out:
        p.stdout.close()
    if err:
        p.stderr.close()


def pipe_processes(cmds, out, err):
    processes = []
    try:
        cmd = "".join(cmds[-1:])
        params = process_params(out, err)
        if cmds[:-1]:
            processes = list(pipe_processes(cmds[:-1], out, err))
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
            close_pipes(p)
        raise e
