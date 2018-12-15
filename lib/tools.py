import os
from contextlib import contextmanager


def resolve(name):
    """
    Copied & pasted directly from the logging module code.
    https://github.com/python/cpython/blob/master/Lib/logging/config.py
    """

    name = name.split('.')
    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used = used + '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)
    return found


@contextmanager
def ensure_folder_exists(path):
    try:
        os.makedirs(path, exist_ok=True)
        yield path
    finally:
        pass
