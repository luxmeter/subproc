from multiprocessing import TimeoutError

import pytest

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import logging
import os
from textwrap import dedent

from subproc import *

filename = os.path.basename(__file__).replace(".py", ".log")
logging.basicConfig(level=logging.DEBUG, filename=filename, filemode='w')
logger = logging.getLogger(os.path.basename(__file__.replace('.py', '')))


def test_run_single_command():
    out = StringIO()
    result = run('echo "hello world"', writer=out.write)
    assert out.getvalue() == "hello world\n"
    assert all([status_code == 0 for cmd, status_code in result])


def test_run_multiple_commands():
    out = StringIO()
    result = run(['echo "hello world"', 'sed "s/hello/bye/g"'], writer=out.write)
    assert out.getvalue() == "bye world\n"
    assert all([status_code == 0 for cmd, status_code in result])


def test_broken_pipe():
    out = StringIO()
    expected = dedent("""\
    read: hello world: 1
    read: hello world: 2
    """)
    # producer prints a line each 0.5s and consumer stop suddenly after receiving the 2nd.
    result = run(['python producer.py', 'python consumer.py'], writer=out.write)
    logger.info('result:' + str(result))
    assert out.getvalue() == expected


def test_timeout():
    # ping pings infinitely, has to be stopped here via timeout
    with pytest.raises(TimeoutError), \
         open(os.devnull, 'w') as out:
        run('ping localhost', writer=out.write, timeoutsec=1)
