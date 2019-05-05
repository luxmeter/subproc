#! env python
from __future__ import print_function

import sys

for i, line in enumerate(iter(sys.stdin.readline, ''), start=1):
    sys.stdout.write('read: ' + line.rstrip() + '\n')
    sys.stdout.flush()
    if i == 3:
        sys.exit(1)
