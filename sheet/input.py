import boon

from .term import invert


class Input:
    def __init__(self, value, submit, cancel, *, prompt='', full=False):
        self.value = value
        self.cursor = len(value)
        self.offset = 0
        self.submit = submit
        self.cancel = cancel
        self.prompt = prompt
        self.full = full

    def scroll_into_view(self, cols):
        if self.cursor < self.offset:
            self.offset = self.cursor
        else:
            space = cols - len(self.prompt) - 1
            if self.cursor > self.offset + space:
                self.offset = self.cursor - space

    def render(self, cols):
        self.scroll_into_view(cols)
        v = self.value + ' '
        return (
            self.prompt
            + v[self.offset:self.cursor]
            + invert(v[self.cursor])
            + v[self.cursor + 1:self.offset + cols - len(self.prompt)]
        )

    def on_key(self, key):
        # TODO ctrl-left/right to jump words
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
        elif key == boon.KEY_DEL:
            if self.cursor < len(self.value):
                self.value = self.value[:self.cursor] + self.value[self.cursor + 1:]
        elif key == chr(27):
            self.cancel()
        elif key == '\n':
            self.submit()
        elif key.isprintable():
            self.value = self.value[:self.cursor] + key + self.value[self.cursor:]
            self.cursor += len(key)
