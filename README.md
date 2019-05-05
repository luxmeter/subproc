# Subproc

Provides utility functions around subprocess module.

## Overview

I guess everyone has its own set of utility methods, especially around the subprocess module.
This is my version :)

## Installation (not yet released)

Install the app (preferred in a [virtual environment](https://realpython.com/python-virtual-environments-a-primer/)):

```bash
pip install subproc
```

## Requirements

I tried to depend only on the Python Stdlib and be backwards compatible to 2.7.
Tested only on unix-like systems :(

## Example

Below is a super artifical code example with its output.
Assuming the snippet is saved to Python script named `example.py` in the current directory, following happens:

- Examing all lines of the script containg an `if`-string (`cat example.py | grep if`)
- Redirect output, line by line, to a writer `padded_writer` (if omitted `sys.stdout.write` is used by default)
- `padded_writer` is a proxy-decorator that adds a left-hand side padding to each line
- By default `padded_writer` redirects the output to `sys.stdout.write` but you can also define another writer (e.g. write method of a `StringIO` instance)
- Here `csvwriter` is writes the to `stdout` and `test.csv`
  - Before that lines are discarded that don't contain the string `csv:`
  - Before writing to `test.csv` the line is trimmed since it comes from the `padded_writer`
- Result is a list of tuples containg the status code to a command

```python
from subproc import run, padded_writer

with open('test.csv', 'w') as csv:
    def csvwriter(line):
        if 'csv:' in line:
            csv.write(line.lstrip().replace('csv:', ''))
            sys.stdout.write(line)
    print('Running command:')
    result = run(['cat example.py', 'grep if'], writer=padded_writer(csvwriter))
    print(result)
```

**Output**

```
Running command:
  if 'csv:' in line:
[('cat ./proc.py', 0), ('grep if', 0)]
```
