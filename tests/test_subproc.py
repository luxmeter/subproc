import os
import time
from textwrap import dedent

import psutil
import pytest

from subproc import DEVNULL, run, run_cmds, run_cmds_redirected, run_redirected

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

WD = os.path.dirname(__file__)

def test_run():
    r = run('echo hello world')
    assert r.return_code == 0, 'Unexpected status code'
    assert r.stdout == 'hello world\n', 'Unexpected output for stdout'
    assert r.stderr == '', 'Unexpected output for stderr'
    assert r.pid > 0, 'Unexpected pid'


def test_run_redirected():
    out = StringIO()
    err = StringIO()
    script = os.path.join(WD, 'scripts', 'echo_all.sh')
    r = run_redirected('bash ' + script, out=out, err=err)
    assert r.return_code == 0, 'Unexpected status code'
    assert out.getvalue() == 'Echoing to stdout\n', 'Unexpected output for stdout'
    assert err.getvalue() == 'Echoing to stderr\n', 'Unexpected output for stderr'


def test_consumes_pipe_correctly():
    # script will load a file which content is greater that the pipe's capacity
    # if the pipe is not consumed correctly, the process will block
    script = os.path.join(WD, 'scripts', 'echo_err.sh')
    r = run_redirected('bash ' + script)
    assert r.return_code == 0, 'Unexpected status code'


def test_timeout():
    r = run('ping localhost', timeoutsec=0.5)
    assert r.return_code != 0, 'Unexpected status code'
    assert 'localhost' in r.stdout, 'Unexpected output for stdout'


def test_os_error():
    with pytest.raises(OSError):
        run('not_existing_command', timeoutsec=0.5)


def test_child_procs_are_killed():
    script = os.path.join(WD, 'scripts', 'background_task.sh')
    r = run('bash ' + script, timeoutsec=0.5)
    with open(os.path.join(WD, 'scripts', 'task.pid')) as f:
        pid = int(f.readlines()[0].strip())
        time.sleep(0.5)
        assert psutil.pid_exists(pid) is False, "Background task still exists"


def test_formatter():
    r = run('echo hello world', formatter=str.upper)
    assert r.stdout == "HELLO WORLD\n", 'Unexpected output for stderr'


def test_redirection_to_file():
    tmpfile = os.path.join(WD, 'scripts', 'tmpfile')
    with open(tmpfile, 'w') as f:
        r = run_redirected('echo hello world', out=f)
    assert r.return_code == 0, 'Unexpected status code'
    assert os.path.exists(tmpfile), 'File does not exists'
    with open(tmpfile, 'r') as f:
        content = f.readlines()[0]
        assert content == "hello world\n", 'Unexpected file content'


def test_piped_cmds():
    result = run_cmds(['echo "hello world"', 'sed "s/hello/bye/g"'])
    assert result.stdout == "bye world\n", 'Unexpected output for stdout'
    assert all([info.return_code == 0 for info in result.infos]), 'Unexpected return code(s)'


def test_piped_command_close_pipe_on_err():
    with pytest.raises(OSError):
        run_cmds_redirected(['echo "hello world"', '"s/hello/bye/g"'])


def test_redirect_to_devnull():
    input = os.path.join(WD, 'scripts', 'content_pipe_sized.txt')
    output = os.path.join(WD, 'scripts', 'test_redirect_to_devnull.txt')
    results = run_cmds_redirected(['cat  ' + input, 'tee ' + output], out=DEVNULL, err=DEVNULL)
    assert all([result.info.return_code == 0 for result in results]), 'Unexpected return code(s)'
    assert os.path.exists(output), 'Output file was not generated'
    with open(output, 'r') as f:
        assert f.readlines(), 'Output file has not content'


def test_broken_pipe():
    expected = dedent("""\
    read: hello world: 1
    read: hello world: 2
    """)
    # producer prints a line each 0.5s and consumer stop suddenly after receiving the 2nd.
    producer = os.path.join(WD, 'scripts', 'producer.py')
    consumer = os.path.join(WD, 'scripts', 'consumer.py')
    results = run_cmds(['python ' + producer, 'python ' + consumer])
    assert results.stdout == expected, 'Unexpected output for stderr'
