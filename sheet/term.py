import boon
from wcwidth import wcswidth

RED = boon.get_cap('setaf', 1)
BLUE = boon.get_cap('setaf', 4)
INVERT = boon.get_cap('rev')
RESET = boon.get_cap('sgr0')


def align_right(s, width):
    w = wcswidth(s)
    if w > width:
        return '#' * width
    return ' ' * (width - w) + s


def align_left(s, width):
    w = wcswidth(s)
    if w > width:
        return '#' * width
    return s + ' ' * (width - w)


def align_center(s, width):
    w = wcswidth(s)
    if w > width:
        return '#' * width
    t = width - w
    return ' ' * (t // 2) + s + ' ' * (t - t // 2)


def red(s):
    return RED + s + RESET


def blue(s):
    return BLUE + s + RESET


def invert(s):
    return INVERT + s + RESET
