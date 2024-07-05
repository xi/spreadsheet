import csv

from .sheet import Sheet


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
            sheet.set((x, y), raw)
    return sheet


def dump_csv(sheet, fh, *, display=False, **kwargs):
    if display:
        def get(cell):
            return to_display(sheet.get_value(cell))
    else:
        get = sheet.get_raw

    width = max(cell[0] for cell in sheet.raw) + 1
    height = max(cell[1] for cell in sheet.raw) + 1

    w = csv.writer(fh, **kwargs)
    for y in range(height):
        w.writerow([get((x, y)) for x in range(width)])
