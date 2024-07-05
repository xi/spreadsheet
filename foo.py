import csv
import re
import string
import sys


class ParseError(ValueError):
    pass


class ReferenceError(ValueError):
    pass


class ExpressionParser:
    def parse_any(self, text, parsers):
        for parser in parsers:
            try:
                return parser(text)
            except ParseError:
                pass
        raise ParseError(f'None of the subparsers matched for {text}')

    def parse_re(self, text, pattern):
        m = re.match(pattern, text)
        if not m:
            raise ParseError
        return m, text[m.end():]

    def parse_string(self, text):
        m, tail = self.parse_re(text, r'"[^"]*"')
        return ('str', m[0][1:-1]), tail

    def parse_float(self, text):
        m, tail = self.parse_re(text, r'[0-9]+\.[0-9]+')
        return ('float', float(m[0])), tail

    def parse_int(self, text):
        m, tail = self.parse_re(text, r'[0-9]+')
        return ('int', int(m[0], 10)), tail

    def parse_ref(self, text):
        m, tail = self.parse_re(text, r'\$?([A-Z]+)\$?([1-9][0-9]*)')
        return ('ref', m[1] + m[2], m[0]), tail

    def parse_range(self, text):
        ref1, tail = self.parse_ref(text)
        _, tail = self.parse_re(tail, r':')
        ref2, tail = self.parse_ref(tail)
        return ('range', ref1, ref2), tail

    def parse_brace(self, text):
        _, tail = self.parse_re(text, r'\(')
        exp, tail = self.parse_expression(tail)
        _, tail = self.parse_re(tail, r'\)')
        return exp, tail

    def parse_add(self, text):
        lhs, tail = self.parse_expression2(text)
        m, tail = self.parse_re(tail, r'\s*[-+]\s*')
        rhs, tail = self.parse_expression(tail)
        return (m[0].strip(), lhs, rhs), tail

    def parse_mul(self, text):
        lhs, tail = self.parse_expression3(text)
        m, tail = self.parse_re(tail, r'\s*[*/]\s*')
        rhs, tail = self.parse_expression2(tail)
        return (m[0].strip(), lhs, rhs), tail

    def parse_call(self, text):
        m, tail = self.parse_re(text, r'[a-zA-Z][a-zA-Z0-9]*')
        _, tail = self.parse_re(tail, r'\(')
        args = []
        if tail.startswith(')'):
            return (m[0], args), tail[1:]
        while True:
            arg, tail = self.parse_expression(tail)
            args.append(arg)
            if tail.startswith(')'):
                return (m[0], args), tail[1:]
            _, tail = self.parse_re(tail, r',\s*')
        raise ParseError

    def parse_expression3(self, text):
        return self.parse_any(text, [
            self.parse_string,
            self.parse_float,
            self.parse_int,
            self.parse_range,
            self.parse_ref,
            self.parse_call,
            self.parse_brace,
        ])

    def parse_expression2(self, text):
        return self.parse_any(text, [
            self.parse_mul,
            self.parse_expression3,
        ])

    def parse_expression(self, text):
        return self.parse_any(text, [
            self.parse_add,
            self.parse_expression2,
        ])

    def parse(self, text):
        expr, tail = self.parse_expression(text)
        if tail:
            raise ParseError(f'unexpected tail: {tail}')
        return expr


def x2col(x):
    a, b = divmod(x, len(string.ascii_uppercase))
    s = string.ascii_uppercase[b]
    while a:
        a, b = divmod(a - 1, len(string.ascii_uppercase))
        s = string.ascii_uppercase[b] + s
    return s


def xy2ref(x, y):
    return x2col(x) + str(y + 1)


def col2x(col):
    alph = string.ascii_uppercase
    x = -1
    for c in col:
        x = (x + 1) * len(alph) + alph.index(c)
    return x


def ref2xy(ref):
    m = re.match('([A-Z]*)([0-9]*)', ref)
    return col2x(m[1]), int(m[2], 10) - 1


def iter_range(cell1, cell2):
    x1, y1 = ref2xy(cell1)
    x2, y2 = ref2xy(cell2)
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            yield xy2ref(x, y)


class Sheet:
    def __init__(self):
        self.expression_parser = ExpressionParser()
        self.reset()

    def reset(self):
        self.raw = {}
        self.parsed = {}
        self.cache = {}
        self.width = 0
        self.height = 0

    def parse(self, raw: str) -> tuple|float|int|str:
        if raw.startswith('='):
            try:
                return self.expression_parser.parse(raw[1:])
            except ParseError as err:
                return ('err', err)
        try:
            return int(raw, 10)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        return raw

    def call_function(self, name: str, args: list[tuple]) -> float|int|str:
        if name == 'sum':
            if len(args) != 1 or args[0][0] != 'range':
                raise ValueError(args)
            _, ref1, ref2 = args[0]
            return sum(
                self.to_number(self.get_value(ref))
                for ref in iter_range(ref1[1], ref2[1])
            )
        elif name == 'power':
            if len(args) != 2:
                raise ValueError(args)
            base = self.to_number(self.evaluate(args[0]))
            exp = self.to_number(self.evaluate(args[1]))
            return base ** exp
        else:
            raise NameError(name)

    def evaluate(self, expr: tuple) -> float|int|str:
        if expr[0] in ['int', 'float', 'str']:
            return expr[1]
        elif expr[0] == 'ref':
            return self.get_value(expr[1])
        elif expr[0] == 'err':
            raise expr[1]
        elif expr[0] == '+':
            return self.evaluate(expr[1]) + self.evaluate(expr[2])
        elif expr[0] == '-':
            return self.evaluate(expr[1]) - self.evaluate(expr[2])
        elif expr[0] == '*':
            return self.evaluate(expr[1]) * self.evaluate(expr[2])
        elif expr[0] == '/':
            return self.evaluate(expr[1]) / self.evaluate(expr[2])
        else:
            return self.call_function(*expr)

    def set(self, cell: str, raw: str):
        if raw:
            self.raw[cell] = raw
            self.parsed[cell] = self.parse(raw)
            x, y = ref2xy(cell)
            self.width = max(self.width, x + 1)
            self.height = max(self.height, y + 1)
        elif cell in self.raw:
            del self.raw[cell]
            del self.parsed[cell]
            self.width = max(ref2xy(cell)[0] for cell in self.raw) + 1
            self.height = max(ref2xy(cell)[1] for cell in self.raw) + 1
        self.cache = {}

    def get_raw(self, cell: str) -> str:
        return self.raw.get(cell, '')

    def get_parsed(self, cell: str) -> tuple|float|int|str|None:
        return self.parsed.get(cell)

    def get_value(self, cell: str) -> float|int|str|None|Exception:
        parsed = self.get_parsed(cell)
        if isinstance(parsed, tuple):
            if cell not in self.cache:
                self.cache[cell] = ReferenceError(cell)
                try:
                    self.cache[cell] = self.evaluate(parsed)
                except Exception as err:
                    self.cache[cell] = err
            return self.cache[cell]
        else:
            return parsed

    def to_number(self, value: float|int|str|None|Exception) -> float|int:
        if isinstance(value, float):
            return value
        elif isinstance(value, int):
            return value
        elif isinstance(value, str):
            raise TypeError(value)
        elif value is None:
            return 0
        elif isinstance(value, Exception):
            raise value

    def to_display(self, value: float|int|str|None|Exception) -> str:
        if isinstance(value, float):
            return str(value)
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, str):
            return value
        elif value is None:
            return ''
        elif isinstance(value, Exception):
            return repr(value)

    def render(self, value: float|int|str|None|Exception, width: int) -> str:
        if isinstance(value, float):
            return align_right(str(value), width)
        elif isinstance(value, int):
            return align_right(str(value), width)
        elif isinstance(value, str):
            return align_left(value, width)
        elif value is None:
            return ' ' * width
        elif isinstance(value, Exception):
            return red(align_left(repr(value), width))

    def load_csv(self, fh, **kwargs):
        self.raw = {}
        self.parsed = {}
        self.cache = {}
        for y, row in enumerate(csv.reader(fh, **kwargs)):
            for x, raw in enumerate(row):
                ref = xy2ref(x, y)
                self.set(ref, raw)

    def write_csv(self, fh, *, display=False, **kwargs):
        if display:
            def get(cell):
                return self.to_display(self.get_value(cell))
        else:
            get = self.get_raw

        w = csv.writer(fh, **kwargs)
        for y in range(self.height):
            w.writerow([get(xy2ref(x, y)) for x in range(self.width)])


def align_right(s, width):
    if len(s) > width:
        s = '###'
    return ' ' + ' ' * (width - len(s) - 1) + s


def align_left(s, width):
    if len(s) > width:
        s = '###'
    return s + ' ' * (width - len(s))


def align_center(s, width):
    if len(s) > width:
        s = '###'
    t = width - len(s)
    return ' ' * (t // 2) + s + ' ' * (t - t // 2)


def red(s):
    return f'\033[31m{s}\033[0m'


def invert(s):
    return f'\033[7m{s}\033[0m'


def render(sheet, width, height, cell_offset, cell_width):
    x0, y0 = ref2xy(cell_offset)
    rows = []
    w = width // cell_width
    rows.append([
        ' ' * cell_width,
    ] + [
        align_center(x2col(x0 + dx), cell_width)
        for dx in range(w - 1)
    ])
    for dy in range(height - 1):
        rows.append([
            align_right(str(y0 + dy + 1), cell_width),
        ] + [
            sheet.render(sheet.get_value(xy2ref(x0 + dx, y0 + dy)), cell_width)
            for dx in range(w - 1)
        ])
    return '\n'.join([''.join(row) for row in rows])


if __name__ == '__main__':
    s = Sheet()
    with open(sys.argv[1]) as fh:
        s.load_csv(fh)

    print(render(s, 80, 40, 'A1', 10))
