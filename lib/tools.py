from contextlib import contextmanager

import numpy as np
import pandas as pd


def fraction_to_float(string):
    # Handle NAs
    if pd.isnull(string):
        return np.nan
    # Parse and check the input string
    aux = string.split('/')
    assert len(aux) in [1, 2], 'The provided string ("{}") is not a number or a fraction'.format(string)
    # Output the computed ratio value as a string
    return aux[0] if len(aux) == 1 else str(float(aux[0])/float(aux[1]))


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass
