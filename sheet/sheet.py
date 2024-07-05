import re
import string

from .expression import ParseError
from .expression import parse


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


def to_number(value: float|int|str|None|Exception) -> float|int:
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


class Sheet:
    def __init__(self):
        self.raw = {}
        self.parsed = {}
        self.cache = {}
        self.width = 0
        self.height = 0

    def parse(self, raw: str) -> tuple|float|int|str:
        if raw.startswith('='):
            try:
                return parse(raw[1:])
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
                to_number(self.get_value(ref))
                for ref in iter_range(ref1[1], ref2[1])
            )
        elif name == 'power':
            if len(args) != 2:
                raise ValueError(args)
            base = to_number(self.evaluate(args[0]))
            exp = to_number(self.evaluate(args[1]))
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
