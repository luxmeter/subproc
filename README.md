# Subproc

Provides utility functions around subprocess module.

## Overview

I guess everyone has its own set of utility methods, especially around the subprocess module.
This is my version :)

## Installation (not yet released)

Install the app (preferred in a [virtual environment](https://realpython.com/python-virtual-environments-a-primer/)):

```bash
pip install subproc==0.0.1.dev1
```

## Requirements

I tried to depend only on the Python Stdlib and be backwards compatible to 2.7.
Tested only on unix-like systems :(

## Examples

Run a command and capture its stdout as well as stderr output:

```python
from subproc import run

r = run('echo hello world')
assert r.return_code == 0
assert r.stdout == 'hello world\n'
assert r.stderr == ''
assert r.pid == 0
```

Run multiple piped commands and capture its stdout as well as stderr output:

```python
from subproc import run_cmds

r = run_cmds(['echo "hello world"', 'sed "s/hello/bye/g"'])
assert r.stdout == "bye world\n"
assert all([info.return_code == 0 for info in r.infos])
```

Run a command and redirect its stdout output to a file

```python
from subproc import run_redirected

with open('temp.log', 'w') as f:
    r = run_redirected('echo hello world', out=f)
    assert r.return_code == 0
with open('temp.log', 'r') as f:
    content = f.readlines()[0]
    assert content == "hello world\n"
```

## Advanced Examples

All methods provided by this module also allow you to define a timeout
as well as a formatter for the line to be printed.

Define a timeout:

```python
from subproc import run
from multiprocessing import TimeoutError

try:
    r = run('ping localhost', timeoutsec=0.5)
except TimeoutError:
    pass
```

Define a formatter:

```python
from subproc import run

r = run('echo hello world', formatter=str.upper)
assert r.stdout == "HELLO WORLD\n"
```
