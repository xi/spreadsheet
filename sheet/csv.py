import csv

from .sheet import Bar
from .sheet import Sheet


def to_display(value: float|int|str|Bar|None|Exception) -> str:
    if isinstance(value, float):
        return str(value)
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        return value
    elif isinstance(value, Bar):
        return value.render(10)
    elif value is None:
        return ''
    elif isinstance(value, Exception):
        return repr(value)


def load_csv(path, **kwargs):
    sheet = Sheet()
    dialect = 'excel-tab' if path.endswith('.tsv') else 'excel'
    with open(path) as fh:
        for y, row in enumerate(csv.reader(fh, dialect=dialect, **kwargs)):
            for x, raw in enumerate(row):
                sheet.set((x, y), raw)
    return sheet


def dump_csv(sheet, path, *, display=False, **kwargs):
    if display:
        def get(cell):
            return to_display(sheet.get_value(cell))
    else:
        get = sheet.get_raw

    width = max((cell[0] for cell in sheet.raw), default=0) + 1
    height = max((cell[1] for cell in sheet.raw), default=0) + 1

    dialect = 'excel-tab' if path.endswith('.tsv') else 'excel'
    with open(path, 'w') as fh:
        w = csv.writer(fh, dialect=dialect, **kwargs)
        for y in range(height):
            w.writerow([get((x, y)) for x in range(width)])
