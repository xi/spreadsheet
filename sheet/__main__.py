import sys

import boon

from .csv import load_csv
from .expression import x2col
from .input import Input
from .sheet import iter_range
from .term import align_center
from .term import align_left
from .term import align_right
from .term import blue
from .term import invert
from .term import red


def to_cell(value: float|int|str|None|Exception, width: int) -> str:
    if isinstance(value, float|int):
        s = f'{{:{width}.{min(width - 2, 6)}g}}'.format(value)
        return align_right(s, width)
    elif isinstance(value, str):
        return align_left(value, width)
    elif value is None:
        return ' ' * width
    elif isinstance(value, Exception):
        return red(align_left(repr(value), width))


class App(boon.App):
    def __init__(self):
        super().__init__()
        with open(sys.argv[1]) as fh:
            self.sheet = load_csv(fh)
        self.x0 = 0
        self.y0 = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.widths = {}
        self.input = None
        self.drag = None

    @property
    def cursor(self):
        return self.cursor_x, self.cursor_y

    def scroll_into_view(self, rows, cols):
        if self.cursor_y < self.y0:
            self.y0 = self.cursor_y
        elif self.cursor_y > self.y0 + rows - 3:
            self.y0 = self.cursor_y - rows + 3

        if self.cursor_x < self.x0:
            self.x0 = self.cursor_x
        else:
            widths = [self.get_width(x) for x in range(self.x0, self.cursor_x + 1)]
            offset = 0
            while sum(widths[offset:]) > cols:
                offset += 1
            self.x0 += offset

    def render(self, rows, cols):
        self.scroll_into_view(rows, cols)

        lines = []

        lines.append(' ' * 4)
        x = self.x0
        width = 4
        while True:
            width += self.get_width(x)
            if width > cols:
                break
            row_head = align_center(x2col(x), self.get_width(x))
            if x == self.cursor_x:
                row_head = invert(row_head)
            lines[-1] += row_head
            x += 1

        for dy in range(rows - 2):
            y = self.y0 + dy
            col_head = align_center(str(y + 1), 4)
            if y == self.cursor_y:
                col_head = invert(col_head)
            lines.append(col_head)

            x = self.x0
            width = 4
            while True:
                width += self.get_width(x)
                if width > cols:
                    break
                value = self.sheet.get_value((x, y))
                cell = to_cell(value, self.get_width(x))
                if (
                    self.drag
                    and min(self.cursor_x, self.drag[0]) <= x
                    and x <= max(self.cursor_x, self.drag[0])
                    and min(self.cursor_y, self.drag[1]) <= y
                    and y <= max(self.cursor_y, self.drag[1])
                ):
                    cell = blue(cell)
                if x == self.cursor_x and y == self.cursor_y:
                    cell = invert(cell)
                lines[-1] += cell
                x += 1

        if self.input:
            lines.append(self.input.render(cols))
        else:
            lines.append(self.sheet.get_raw(self.cursor))

        return lines

    def get_width(self, x):
        return self.widths.get(x, 10)

    def set_width(self, x, value):
        self.widths[x] = max(value, 3)

    def change_width(self, x, d):
        old = self.get_width(x)
        self.set_width(x, old + d)

    def submit_input(self):
        self.sheet.set(self.cursor, self.input.value)
        self.input = None

    def cancel_input(self):
        self.input = None

    def submit_drag(self):
        value = self.sheet.get_raw(self.drag)
        for x, y in iter_range(self.cursor, self.drag):
            # TODO: modify references in expression
            self.sheet.set((x, y), value)
        self.drag = None

    def cancel_drag(self):
        self.drag = None

    def on_key(self, key):
        if self.input:
            if not self.input.full and key in [
                boon.KEY_DOWN,
                boon.KEY_UP,
                boon.KEY_NPAGE,
                boon.KEY_PPAGE,
                boon.KEY_RIGHT,
                boon.KEY_LEFT,
            ]:
                self.submit_input()
                self.on_key(key)
            else:
                self.input.on_key(key)
        elif key == 'q':
            self.running = False
        elif key == boon.KEY_DOWN:
            self.cursor_y += 1
        elif key == boon.KEY_UP:
            self.cursor_y = max(self.cursor_y - 1, 0)
        elif key == boon.KEY_NPAGE:
            self.cursor_y += self.rows - 3
        elif key == boon.KEY_PPAGE:
            self.cursor_y = max(self.cursor_y - (self.rows - 3), 0)
        elif key == boon.KEY_RIGHT:
            self.cursor_x += 1
        elif key == boon.KEY_LEFT:
            self.cursor_x = max(self.cursor_x - 1, 0)
        elif self.drag is not None:
            if key == '\n':
                self.submit_drag()
            elif key == boon.KEY_ESC:
                self.cancel_drag()
        elif key == '>':
            self.change_width(self.cursor_x, 1)
        elif key == '<':
            self.change_width(self.cursor_x, -1)
        elif key == '\n':
            raw = self.sheet.get_raw(self.cursor)
            self.input = Input(raw, self.submit_input, self.cancel_input, full=True)
        elif key in '=0123456789':
            self.input = Input(key, self.submit_input, self.cancel_input, full=False)
        elif key == boon.KEY_DEL:
            self.sheet.set(self.cursor, '')
        elif key == '#':
            self.drag = self.cursor


app = App()
app.run()
