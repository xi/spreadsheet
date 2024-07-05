from .expression import x2col


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


def to_cell(value: float|int|str|None|Exception, width: int) -> str:
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


def render(sheet, width, height, cell_offset, cell_width):
    x0, y0 = cell_offset
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
            to_cell(sheet.get_value((x0 + dx, y0 + dy)), cell_width)
            for dx in range(w - 1)
        ])
    return '\n'.join([''.join(row) for row in rows])
