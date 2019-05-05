#! env python
from __future__ import print_function

import sys
import time

for i in range(1, 10):
    sys.stdout.write("hello world: {}\n".format(i))
    sys.stdout.flush()
    time.sleep(0.5)
