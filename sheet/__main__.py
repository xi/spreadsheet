import sys

from .csv import load_csv
from .term import render

with open(sys.argv[1]) as fh:
    sheet = load_csv(fh)

print(render(sheet, 80, 40, (0, 0), 10))
