from __future__ import print_function

import sys
from functools import wraps


def padded_writer(writer=sys.stdout.write, padding=4, prefix=""):
    @wraps(writer)
    def decorated(line, *args, **kwargs):
        formatted_line = padding * ' ' + prefix + line
        return writer(formatted_line, *args, **kwargs)

    return decorated
