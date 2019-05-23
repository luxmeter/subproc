import logging
import os
import time
from multiprocessing import TimeoutError
from textwrap import dedent

import psutil
import pytest

from subproc import subproc2

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

filename = os.path.basename(__file__).replace('.py', '.log')
logging.basicConfig(level=logging.DEBUG, filename=filename, filemode='w',
                    format='%(levelname)-5s | %(threadName)-10s | %(message)s')
logging.addLevelName(logging.WARNING, 'WARN')
logger = logging.getLogger(os.path.basename(__file__.replace('.py', '')))


def test_run():
    r = subproc2.run('echo hello world')
    assert r.return_code == 0, 'Unexpected status code'
    assert r.stdout == 'hello world\n', 'Unexpected output for stdout'
    assert r.stderr == '', 'Unexpected output for stderr'
    assert r.pid > 0, 'Unexpected pid'


def test_run_to_file():
    out = StringIO()
    err = StringIO()
    r = subproc2.run_redirected('echo hello world', out=out, err=err)
    assert r.return_code == 0, 'Unexpected status code'
    assert out.getvalue() == 'hello world\n', 'Unexpected output for stdout'
    assert err.getvalue() == '', 'Unexpected output for stderr'
    assert r.pid > 0, 'Unexpected pid'


def test_run_to_file_stderr():
    out = StringIO()
    err = StringIO()
    r = subproc2.run_redirected('bash echo_all.sh', out=out, err=err)
    assert r.return_code == 0, 'Unexpected status code'
    assert out.getvalue() == 'Echoing to stdout\n', 'Unexpected output for stdout'
    assert err.getvalue() == 'Echoing to stderr\n', 'Unexpected output for stderr'


def test_run_to_file_not_blocking():
    r = subproc2.run_redirected('bash echo_err.sh')
    assert r.return_code == 0, 'Unexpected status code'


def test_run_not_blocking():
    with pytest.raises(TimeoutError):
        r = subproc2.run('ping localhost', timeoutsec=0.5)
        assert r.return_code == 0, 'Unexpected status code'


def test_os_error():
    with pytest.raises(OSError):
        subproc2.run('not_existing_command', timeoutsec=0.5)


def test_kill_child_process():
    with pytest.raises(TimeoutError):
        subproc2.run('bash background_task.sh', timeoutsec=0.5)
    with open('task.pid') as f:
        pid = int(f.readlines()[0].strip())
        time.sleep(0.5)
        assert psutil.pid_exists(pid) is False, "Background task still exists"


def test_formatter():
    r = subproc2.run('echo hello world', formatter=str.upper)
    assert r.stdout == "HELLO WORLD\n", 'Unexpected output for stderr'


def test_file_redirection():
    with open('tmpfile', 'w') as f:
        r = subproc2.run_redirected('echo hello world', out=f)
    assert r.return_code == 0, 'Unexpected status code'
    assert os.path.exists('tmpfile'), 'File does not exists'
    with open('tmpfile', 'r') as f:
        content = f.readlines()[0]
        assert content == "hello world\n", 'Unexpected file content'


def test_run_multiple_commands():
    result = subproc2.run_cmds(['echo "hello world"', 'sed "s/hello/bye/g"'])
    assert result.stdout == "bye world\n"
    assert all([info.return_code == 0 for info in result.infos])


def test_broken_pipe():
    expected = dedent("""\
    read: hello world: 1
    read: hello world: 2
    """)
    # producer prints a line each 0.5s and consumer stop suddenly after receiving the 2nd.
    results = subproc2.run_cmds(['python producer.py', 'python consumer.py'])
    assert results.stdout == expected
