import math
from collections.abc import Callable
from collections.abc import Generator

from . import expression

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


Cell = tuple[int, int]
RawValue = float | int | str
Parsed = RawValue | expression.Expr | expression.ParseError
Value = RawValue | Bar | None | Exception


FUNCTIONS: dict[str, tuple[Callable, str | int]] = {
    'sum': (sum, 'range'),
    'min': (min, 'range'),
    'max': (max, 'range'),
    'power': (math.pow, 2),
    'exp': (math.exp, 1),
    'sin': (math.sin, 1),
    'cos': (math.cos, 1),
    'tan': (math.tan, 1),
    'log': (math.log, 1),
    'bar': (Bar, 1),
}


def iter_range(cell1: Cell, cell2: Cell) -> Generator[Cell, None, None]:
    x1, y1 = cell1
    x2, y2 = cell2
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            yield x, y


def to_number(value: Value) -> float | int:
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
        self.raw: dict[Cell, str] = {}
        self.parsed: dict[Cell, Parsed] = {}
        self.cache: dict[Cell, Value] = {}

    def parse(self, raw: str) -> Parsed:
        if raw.startswith('='):
            try:
                return expression.parse(raw[1:])
            except expression.ParseError as err:
                return err
        try:
            return int(raw, 10)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        return raw

    def call_function(self, name: str, args: list[expression.Expr]) -> Value:
        fn, nargs = FUNCTIONS[name.lower()]
        if nargs == 'range':
            if len(args) != 1 or not isinstance(args[0], expression.Range):
                raise ValueError(args)
            return fn(
                to_number(self.get_value(ref))
                for ref in iter_range(args[0].start.cell, args[0].end.cell)
            )
        else:
            if len(args) != nargs:
                raise ValueError(args)
            return fn(*[to_number(self.evaluate(a)) for a in args])

    def evaluate(self, expr: expression.Expr) -> Value:
        if isinstance(expr, (expression.Int, expression.Float, expression.String)):
            return expr.value
        elif isinstance(expr, expression.Ref):
            return self.get_value(expr.cell)
        elif isinstance(expr, expression.Brace):
            return self.evaluate(expr.inner)
        elif isinstance(expr, expression.Op):
            lhs = to_number(self.evaluate(expr.lhs))
            rhs = to_number(self.evaluate(expr.rhs))
            if expr.op == '+':
                return lhs + rhs
            elif expr.op == '-':
                return lhs - rhs
            elif expr.op == '*':
                return lhs * rhs
            elif expr.op == '/':
                return lhs / rhs
        elif isinstance(expr, expression.Call):
            return self.call_function(expr.name, expr.args)
        raise ValueError(expr)

    def set(self, cell: Cell, raw: str):
        if raw:
            self.raw[cell] = raw
            self.parsed[cell] = self.parse(raw)
        elif cell in self.raw:
            del self.raw[cell]
            del self.parsed[cell]
        self.cache = {}

    def set_shifted(self, cell: Cell, raw: str, shift: Cell):
        if raw.startswith('='):
            expr = self.parse(raw)
            if isinstance(expr, expression.Expr):
                shifted = expr.shift_refs(shift)
                raw = f'={shifted.unparse()}'
        self.set(cell, raw)

    def get_raw(self, cell: Cell) -> str:
        return self.raw.get(cell, '')

    def get_parsed(self, cell: Cell) -> Parsed | None:
        return self.parsed.get(cell)

    def get_value(self, cell: Cell) -> Value:
        parsed = self.get_parsed(cell)
        if isinstance(parsed, expression.Expr):
            if cell not in self.cache:
                self.cache[cell] = ReferenceError(cell)
                try:
                    self.cache[cell] = self.evaluate(parsed)
                except Exception as err:
                    self.cache[cell] = err
            return self.cache[cell]
        else:
            return parsed
