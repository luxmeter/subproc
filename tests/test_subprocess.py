try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from textwrap import dedent

from subproc import *


def test_run_single_command():
    out = StringIO()
    run('echo "hello world"', writer=out.write)
    assert out.getvalue() == "hello world\n"


def test_run_multiple_commands():
    out = StringIO()
    run(['echo "hello world"', 'sed "s/hello/bye/g"'], writer=out.write)
    assert out.getvalue() == "bye world\n"


def test_nodeadlock():
    out = StringIO()
    expected = dedent("""\
    read: hello world: 1
    read: hello world: 2
    read: hello world: 3
    """)
    run(['python producer.py', 'python consumer.py'], writer=out.write)
    assert out.getvalue() == expected
