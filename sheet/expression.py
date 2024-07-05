import re
import string


class ParseError(ValueError):
    pass


def parse_any(text, parsers):
    for parser in parsers:
        try:
            return parser(text)
        except ParseError:
            pass
    raise ParseError(f'None of the subparsers matched for {text}')


def parse_re(text, pattern):
    m = re.match(pattern, text)
    if not m:
        raise ParseError
    return m, text[m.end():]


def parse_string(text):
    m, tail = parse_re(text, r'"[^"]*"')
    return ('str', m[0][1:-1]), tail


def parse_float(text):
    m, tail = parse_re(text, r'[0-9]+\.[0-9]+')
    return ('float', float(m[0])), tail


def parse_int(text):
    m, tail = parse_re(text, r'[0-9]+')
    return ('int', int(m[0], 10)), tail


def col2x(col):
    alph = string.ascii_uppercase
    x = -1
    for c in col:
        x = (x + 1) * len(alph) + alph.index(c)
    return x


def x2col(x):
    a, b = divmod(x, len(string.ascii_uppercase))
    s = string.ascii_uppercase[b]
    while a:
        a, b = divmod(a - 1, len(string.ascii_uppercase))
        s = string.ascii_uppercase[b] + s
    return s


def parse_ref(text):
    m, tail = parse_re(text, r'(\$)?([A-Z]+)(\$)?([1-9][0-9]*)')
    x_fixed = bool(m[1])
    x = col2x(m[2])
    y_fixed = bool(m[3])
    y = int(m[4], 10) - 1
    return ('ref', (x, y), (x_fixed, y_fixed)), tail


def parse_range(text):
    ref1, tail = parse_ref(text)
    _, tail = parse_re(tail, r':')
    ref2, tail = parse_ref(tail)
    return ('range', ref1, ref2), tail


def parse_brace(text):
    _, tail = parse_re(text, r'\(')
    exp, tail = parse_expression(tail)
    _, tail = parse_re(tail, r'\)')
    return exp, tail


def parse_add(text):
    lhs, tail = parse_expression2(text)
    m, tail = parse_re(tail, r'\s*[-+]\s*')
    rhs, tail = parse_expression(tail)
    return (m[0].strip(), lhs, rhs), tail


def parse_mul(text):
    lhs, tail = parse_expression3(text)
    m, tail = parse_re(tail, r'\s*[*/]\s*')
    rhs, tail = parse_expression2(tail)
    return (m[0].strip(), lhs, rhs), tail


def parse_call(text):
    m, tail = parse_re(text, r'[a-zA-Z][a-zA-Z0-9]*')
    _, tail = parse_re(tail, r'\(')
    args = []
    if tail.startswith(')'):
        return (m[0], args), tail[1:]
    while True:
        arg, tail = parse_expression(tail)
        args.append(arg)
        if tail.startswith(')'):
            return (m[0], args), tail[1:]
        _, tail = parse_re(tail, r',\s*')
    raise ParseError('no closing brace on function call')


def parse_expression3(text):
    return parse_any(text, [
        parse_string,
        parse_float,
        parse_int,
        parse_range,
        parse_ref,
        parse_call,
        parse_brace,
    ])


def parse_expression2(text):
    return parse_any(text, [
        parse_mul,
        parse_expression3,
    ])


def parse_expression(text):
    return parse_any(text, [
        parse_add,
        parse_expression2,
    ])


def parse(text):
    expr, tail = parse_expression(text)
    if tail:
        raise ParseError(f'unexpected tail: {tail}')
    return expr
