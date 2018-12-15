
def fraction_to_float(string):
    # Parse and check the input string
    aux = string.split('/')
    assert len(aux) in [1, 2], 'The provided string ("{}") is not a number or a fraction'.format(string)
    # Output the computed ratio value as a string
    return aux[0] if len(aux) == 1 else str(float(aux[0])/float(aux[1]))


def percentage_to_float(string):
    return str(float(string.rstrip('%')) / 100)


def comma_to_dot_float(string):
    return string.replace(',', '.')


def simple_quote_to_double_simple_quote(string):
    return string.replace("'", "''")
