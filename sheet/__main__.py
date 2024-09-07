import argparse

import boon
from wcwidth import wcswidth

from .csv import dump_csv
from .csv import load_csv
from .expression import x2col
from .input import Input
from .sheet import Bar
from .sheet import Sheet
from .sheet import iter_range
from .term import align_center
from .term import align_left
from .term import align_right
from .term import blue
from .term import green
from .term import invert
from .term import red

HELP = """
Help
---

arrow keys   - move the cursor
page up/down - move one screen up/down
enter        - start edit mode
=, -, 0-9    - start quick edit mode
#            - start drag mode
v            - start visual mode
del          - delete
>, <         - adjust column width
w            - write to file (source form)
W            - write to file (evaluated form)
h            - show help
q            - quit
"""


def to_cell(value: float|int|str|None|Exception, width: int) -> str:
    if isinstance(value, float|int):
        s = f'{{:{width}.{min(width - 2, 6)}g}}'.format(value)
        return align_right(s, width)
    elif isinstance(value, str):
        return align_left(value, width)
    elif isinstance(value, Bar):
        return value.render(width)
    elif value is None:
        return ' ' * width
    elif isinstance(value, Exception):
        return red(align_left(repr(value), width))


class App(boon.App):
    def __init__(self, path=None):
        super().__init__()
        self.path = path or ''
        if path:
            self.sheet = load_csv(self.path)
        else:
            self.sheet = Sheet()
        self.x0 = 0
        self.y0 = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.widths = {}
        self.input = None
        self.drag = None
        self.visual = None
        self.clipboard_pos = (0, 0)
        self.clipboard = [[]]
        self.help = False

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
            while 4 + sum(widths[offset:]) > cols:
                offset += 1
            self.x0 += offset

    def render(self, rows, cols):
        if self.help:
            lines = HELP.strip().split('\n')
            max_width = max(wcswidth(line) for line in lines)
            x_offset = max(0, cols - max_width) // 2
            y_offset = max(0, rows - len(lines)) // 2
            for _ in range(y_offset):
                yield ''
            for line in lines:
                yield ' ' * x_offset + line
            return

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
                elif (
                    self.visual
                    and min(self.cursor_x, self.visual[0]) <= x
                    and x <= max(self.cursor_x, self.visual[0])
                    and min(self.cursor_y, self.visual[1]) <= y
                    and y <= max(self.cursor_y, self.visual[1])
                ):
                    cell = green(cell)
                if x == self.cursor_x and y == self.cursor_y:
                    cell = invert(cell)
                lines[-1] += cell
                x += 1

        if self.input:
            lines.append(self.input.render(cols))
        else:
            lines.append(self.sheet.get_raw(self.cursor))

        yield from lines

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

    def submit_write(self):
        self.path = self.input.value
        dump_csv(self.sheet, self.input.value)
        self.input = None

    def submit_write_eval(self):
        dump_csv(self.sheet, self.input.value, display=True)
        self.input = None

    def submit_drag(self):
        raw = self.sheet.get_raw(self.drag)
        for x, y in iter_range(self.cursor, self.drag):
            shift = (x - self.drag[0], y - self.drag[1])
            self.sheet.set_shifted((x, y), raw, shift)
        self.drag = None

    def cancel_drag(self):
        self.drag = None

    def copy(self):
        x1, x2 = sorted((self.cursor_x, self.visual[0]))
        y1, y2 = sorted((self.cursor_y, self.visual[1]))
        self.clipboard_pos = (x1, y1)
        self.clipboard = [
            [self.sheet.get_raw((x, y)) for x in range(x1, x2 + 1)]
            for y in range(y1, y2 + 1)
        ]

    def paste(self):
        shift = (
            self.cursor_x - self.clipboard_pos[0],
            self.cursor_y - self.clipboard_pos[1],
        )
        for dy, row in enumerate(self.clipboard):
            for dx, raw in enumerate(row):
                pos = (self.cursor_x + dx, self.cursor_y + dy)
                self.sheet.set_shifted(pos, raw, shift)

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
        elif key == 'h':
            self.help = not self.help
        elif key == 'q' and self.help:
            self.help = False
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
        elif self.visual is not None:
            if key in ['y', 'd', boon.KEY_DEL]:
                self.copy()
                if key in ['d', boon.KEY_DEL]:
                    for pos in iter_range(self.cursor, self.visual):
                        self.sheet.set(pos, '')
                self.cursor_x, self.cursor_y = self.visual
                self.visual = None
            elif key in ['\n', boon.KEY_ESC]:
                self.visual = None
        elif key == 'p':
            self.paste()
        elif key == '>':
            self.change_width(self.cursor_x, 1)
        elif key == '<':
            self.change_width(self.cursor_x, -1)
        elif key == '\n':
            raw = self.sheet.get_raw(self.cursor)
            self.input = Input(raw, self.submit_input, self.cancel_input, full=True)
        elif key in '-=0123456789':
            self.input = Input(key, self.submit_input, self.cancel_input, full=False)
        elif key == boon.KEY_DEL:
            self.sheet.set(self.cursor, '')
        elif key == '#':
            self.drag = self.cursor
        elif key == 'v':
            self.visual = self.cursor
        elif key == 'w':
            self.input = Input(
                self.path,
                self.submit_write,
                self.cancel_input,
                prompt='Write: ',
                full=True,
            )
        elif key == 'W':
            self.input = Input(
                self.path,
                self.submit_write_eval,
                self.cancel_input,
                prompt='Write (evaluated): ',
                full=True,
            )


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', default='', nargs='?')
    parser.add_argument('--eval')
    return parser


def main():
    args = get_parser().parse_args()
    if args.eval:
        if not args.path:
            raise ValueError('path missing')
        sheet = load_csv(args.path)
        dump_csv(sheet, args.eval, display=True)
    else:
        app = App(args.path)
        app.run()


if __name__ == '__main__':
    main()
