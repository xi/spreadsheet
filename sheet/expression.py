import abc
import re
import string
from dataclasses import dataclass


class ParseError(ValueError):
    pass


class Expr(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def parse(cls, text: str) -> tuple['Expr', str]:
        ...

    @abc.abstractmethod
    def unparse(self) -> str:
        ...

    @abc.abstractmethod
    def shift_refs(self, d: tuple[int, int]) -> 'Expr':
        ...


def parse_re(text: str, pattern: str) -> tuple[re.Match, str]:
    m = re.match(pattern, text)
    if not m:
        raise ParseError
    return m, text[m.end():]


def parse_any(text: str, parsers: list) -> tuple[Expr, str]:
    for parser in parsers:
        try:
            return parser(text)
        except ParseError:
            pass
    raise ParseError(f'None of the subparsers matched for {text}')


def col2x(col: str) -> int:
    alph = string.ascii_uppercase
    x = -1
    for c in col:
        x = (x + 1) * len(alph) + alph.index(c)
    return x


def x2col(x: int) -> str:
    if x < 0:
        return '#'
    a, b = divmod(x, len(string.ascii_uppercase))
    s = string.ascii_uppercase[b]
    while a:
        a, b = divmod(a - 1, len(string.ascii_uppercase))
        s = string.ascii_uppercase[b] + s
    return s


@dataclass(frozen=True)
class String(Expr):
    value: str
    raw: str

    @classmethod
    def parse(cls, text: str) -> tuple['String', str]:
        m, tail = parse_re(text, r'"[^"]*"')
        return cls(m[0][1:-1], m[0]), tail

    def unparse(self) -> str:
        return self.raw

    def shift_refs(self, d: tuple[int, int]) -> 'String':
        return self


@dataclass(frozen=True)
class Float(Expr):
    value: float
    raw: str

    @classmethod
    def parse(cls, text: str) -> tuple['Float', str]:
        m, tail = parse_re(text, r'[0-9]+\.[0-9]+')
        return cls(float(m[0]), m[0]), tail

    def unparse(self) -> str:
        return self.raw

    def shift_refs(self, d: tuple[int, int]) -> 'Float':
        return self


@dataclass(frozen=True)
class Int(Expr):
    value: int
    raw: str

    @classmethod
    def parse(cls, text: str) -> tuple['Int', str]:
        m, tail = parse_re(text, r'[0-9]+')
        return cls(int(m[0], 10), m[0]), tail

    def unparse(self) -> str:
        return self.raw

    def shift_refs(self, d: tuple[int, int]) -> 'Int':
        return self


@dataclass(frozen=True)
class Ref(Expr):
    cell: tuple[int, int]
    fixed: tuple[bool, bool]

    @classmethod
    def parse(cls, text: str) -> tuple['Ref', str]:
        m, tail = parse_re(text, r'(\$)?([A-Z]+)(\$)?([1-9][0-9]*)')
        x_fixed = bool(m[1])
        x = col2x(m[2])
        y_fixed = bool(m[3])
        y = int(m[4], 10) - 1
        return cls((x, y), (x_fixed, y_fixed)), tail

    def unparse(self) -> str:
        s = ''
        s += '$' if self.fixed[0] else ''
        s += x2col(self.cell[0])
        s += '$' if self.fixed[1] else ''
        s += str(self.cell[1] + 1)
        return s

    def shift_refs(self, d: tuple[int, int]) -> 'Ref':
        x, y = self.cell
        if not self.fixed[0]:
            x += d[0]
        if not self.fixed[1]:
            y += d[1]
        return Ref((x, y), self.fixed)


@dataclass(frozen=True)
class Range(Expr):
    start: Ref
    end: Ref

    @classmethod
    def parse(cls, text: str) -> tuple['Range', str]:
        ref1, tail = Ref.parse(text)
        _, tail = parse_re(tail, r':')
        ref2, tail = Ref.parse(tail)
        return cls(ref1, ref2), tail

    def unparse(self) -> str:
        return f'{self.start.unparse()}:{self.end.unparse()}'

    def shift_refs(self, d: tuple[int, int]) -> 'Range':
        return Range(self.start.shift_refs(d), self.end.shift_refs(d))


@dataclass(frozen=True)
class Brace(Expr):
    inner: Expr

    @classmethod
    def parse(cls, text: str) -> tuple['Brace', str]:
        _, tail = parse_re(text, r'\(')
        exp, tail = Op.parse(tail)
        _, tail = parse_re(tail, r'\)')
        return cls(exp), tail

    def unparse(self) -> str:
        return f'({self.inner.unparse()})'

    def shift_refs(self, d: tuple[int, int]) -> 'Brace':
        return Brace(self.inner.shift_refs(d))


@dataclass(frozen=True)
class Call(Expr):
    name: str
    args: list[Expr]
    commas: list[str]

    @classmethod
    def parse(cls, text: str) -> tuple['Call', str]:
        m, tail = parse_re(text, r'[a-zA-Z][a-zA-Z0-9]*')
        _, tail = parse_re(tail, r'\(')
        args = []
        commas = []
        if tail.startswith(')'):
            return cls(m[0], args, commas), tail[1:]
        while True:
            arg, tail = Op.parse(tail)
            args.append(arg)
            if tail.startswith(')'):
                return cls(m[0], args, commas), tail[1:]
            c, tail = parse_re(tail, r',\s*')
            commas.append(c[0])
        raise ParseError('no closing brace on function call')

    def unparse(self) -> str:
        assert len(self.args) == len(self.commas) + 1
        sargs = ''
        if self.args:
            for i, comma in enumerate(self.commas):
                sargs += str(self.args[i].unparse()) + comma
            sargs += str(self.args[-1].unparse())
        return f'{self.name}({sargs})'

    def shift_refs(self, d: tuple[int, int]) -> 'Call':
        return Call(
            self.name,
            [arg.shift_refs(d) for arg in self.args],
            self.commas,
        )


@dataclass(frozen=True)
class Op(Expr):
    op: str
    lhs: Expr
    rhs: Expr
    op_raw: str

    @classmethod
    def _parse(cls, text: str, pattern: str, parse_child) -> tuple['Op', str]:
        lhs, tail = parse_child(text)
        while True:
            try:
                m, tail = parse_re(tail, pattern)
            except ParseError:
                break
            rhs, tail = parse_child(tail)
            lhs = cls(m[0].strip(), lhs, rhs, m[0])
        return lhs, tail

    @classmethod
    def parse_basic(cls, text: str) -> tuple[Expr, str]:
        return parse_any(text, [
            String.parse,
            Float.parse,
            Int.parse,
            Range.parse,
            Ref.parse,
            Call.parse,
            Brace.parse,
        ])

    @classmethod
    def parse_mult(cls, text: str) -> tuple['Op', str]:
        return cls._parse(text, r'\s*[*/]\s*', cls.parse_basic)

    @classmethod
    def parse(cls, text: str) -> tuple['Op', str]:
        return cls._parse(text, r'\s*[-+]\s*', cls.parse_mult)

    def unparse(self) -> str:
        return f'{self.lhs.unparse()}{self.op_raw}{self.rhs.unparse()}'

    def shift_refs(self, d: tuple[int, int]) -> 'Op':
        return Op(
            self.op,
            self.lhs.shift_refs(d),
            self.rhs.shift_refs(d),
            self.op_raw,
        )


def parse(text: str) -> Expr:
    expr, tail = Op.parse(text)
    if tail:
        raise ParseError(f'unexpected tail: {tail}')
    return expr
