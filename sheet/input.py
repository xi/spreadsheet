import string

import boon

from .term import invert


class Input:
    def __init__(self, value, submit, cancel):
        self.value = value
        self.cursor = len(value)
        self.offset = 0
        self.submit = submit
        self.cancel = cancel

    def scroll_into_view(self, cols):
        if self.cursor < self.offset:
            self.offset = self.cursor
        elif self.cursor > self.offset + cols - 1:
            self.offset = self.cursor - cols + 1

    def render(self, cols):
        self.scroll_into_view(cols)
        v = self.value + ' '
        return (
            v[self.offset:self.cursor]
            + invert(v[self.cursor])
            + v[self.cursor + 1:self.offset + cols]
        )

    def on_key(self, key):
        # TODO ctrl-left/right to jump words
        # TODO del
        if key == boon.KEY_LEFT:
            self.cursor = max(self.cursor - 1, 0)
        elif key == boon.KEY_RIGHT:
            self.cursor = min(self.cursor + 1, len(self.value))
        elif key == boon.KEY_HOME:
            self.cursor = 0
        elif key == boon.KEY_END:
            self.cursor = len(self.value)
        elif key == boon.KEY_BACKSPACE:
            if self.cursor > 0:
                self.value = self.value[:self.cursor - 1] + self.value[self.cursor:]
                self.cursor -= 1
        elif key == chr(27):
            self.cancel()
        elif key == '\n':
            self.submit()
        elif key.isprintable():
            self.value += key
            self.cursor += len(key)
        else:
            self.value += repr(key)
            self.cursor += len(repr(key))
