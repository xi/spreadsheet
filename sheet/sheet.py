
from .expression import ParseError
from .expression import parse
from .expression import shift_refs
from .expression import unparse

BLOCKS = [' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']


class Bar:
    def __init__(self, value):
        self.value = value

    def render(self, width):
        value = max(0, min(1, self.value))
        x = round(value * width * (len(BLOCKS) - 1))
        a, b = divmod(x, len(BLOCKS) - 1)
        if a == width:
            return a * BLOCKS[-1]
        else:
            return a * BLOCKS[-1] + BLOCKS[b] + (width - a - 1) * BLOCKS[0]


def iter_range(cell1, cell2):
    x1, y1 = cell1
    x2, y2 = cell2
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            yield x, y


def to_number(value: float|int|str|Bar|None|Exception) -> float|int:
    if isinstance(value, float):
        return value
    elif isinstance(value, int):
        return value
    elif isinstance(value, str):
        raise TypeError(value)
    elif isinstance(value, Bar):
        return value.value
    elif value is None:
        return 0
    elif isinstance(value, Exception):
        raise value


class Sheet:
    def __init__(self):
        self.raw = {}
        self.parsed = {}
        self.cache = {}

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

    def call_function(
        self, name: str, args: list[tuple], _commas: list[str]
    ) -> float|int|str|Bar:
        if name.lower() == 'sum':
            if len(args) != 1 or args[0][0] != 'range':
                raise ValueError(args)
            _, ref1, ref2 = args[0]
            return sum(
                to_number(self.get_value(ref))
                for ref in iter_range(ref1[1], ref2[1])
            )
        elif name.lower() == 'power':
            if len(args) != 2:
                raise ValueError(args)
            base = to_number(self.evaluate(args[0]))
            exp = to_number(self.evaluate(args[1]))
            return base ** exp
        elif name.lower() == 'bar':
            if len(args) != 1:
                raise ValueError(args)
            return Bar(to_number(self.evaluate(args[0])))
        else:
            raise NameError(name)

    def evaluate(self, expr: tuple) -> float|int|str|Bar:
        if expr[0] in ['int', 'float', 'str']:
            return expr[1]
        elif expr[0] == 'ref':
            return self.get_value(expr[1])
        elif expr[0] == 'brace':
            return self.evaluate(expr[1])
        elif expr[0] == 'err':
            raise expr[1]
        elif expr[0] == '+':
            lhs = to_number(self.evaluate(expr[1]))
            rhs = to_number(self.evaluate(expr[2]))
            return lhs + rhs
        elif expr[0] == '-':
            lhs = to_number(self.evaluate(expr[1]))
            rhs = to_number(self.evaluate(expr[2]))
            return lhs - rhs
        elif expr[0] == '*':
            lhs = to_number(self.evaluate(expr[1]))
            rhs = to_number(self.evaluate(expr[2]))
            return lhs * rhs
        elif expr[0] == '/':
            lhs = to_number(self.evaluate(expr[1]))
            rhs = to_number(self.evaluate(expr[2]))
            return lhs / rhs
        else:
            return self.call_function(*expr)

    def set(self, cell, raw: str):
        if raw:
            self.raw[cell] = raw
            self.parsed[cell] = self.parse(raw)
            x, y = cell
        elif cell in self.raw:
            del self.raw[cell]
            del self.parsed[cell]
        self.cache = {}

    def set_shifted(self, cell, raw: str, shift) -> str:
        if raw.startswith('='):
            expr = self.parse(raw)
            shifted = shift_refs(expr, shift)
            raw = '=' + unparse(shifted)
        self.set(cell, raw)

    def get_raw(self, cell) -> str:
        return self.raw.get(cell, '')

    def get_parsed(self, cell) -> tuple|float|int|str|None:
        return self.parsed.get(cell)

    def get_value(self, cell) -> float|int|str|Bar|None|Exception:
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
