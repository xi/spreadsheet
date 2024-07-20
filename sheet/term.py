from wcwidth import wcswidth


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
    return f'\033[31m{s}\033[0m'


def blue(s):
    return f'\033[34m{s}\033[0m'


def invert(s):
    return f'\033[7m{s}\033[0m'
