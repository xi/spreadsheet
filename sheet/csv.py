import csv

from .sheet import Sheet
from .sheet import xy2ref


def to_display(value: float|int|str|None|Exception) -> str:
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


def load_csv(fh, **kwargs):
    sheet = Sheet()
    for y, row in enumerate(csv.reader(fh, **kwargs)):
        for x, raw in enumerate(row):
            ref = xy2ref(x, y)
            sheet.set(ref, raw)
    return sheet


def dump_csv(sheet, fh, *, display=False, **kwargs):
    if display:
        def get(cell):
            return to_display(sheet.get_value(cell))
    else:
        get = sheet.get_raw

    w = csv.writer(fh, **kwargs)
    for y in range(sheet.height):
        w.writerow([get(xy2ref(x, y)) for x in range(sheet.width)])
