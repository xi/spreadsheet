def align_right(s, width):
    if len(s) > width:
        s = '###'
    return ' ' * (width - len(s)) + s


def align_left(s, width):
    if len(s) > width:
        s = '###'
    return s + ' ' * (width - len(s))


def align_center(s, width):
    if len(s) > width:
        s = '###'
    t = width - len(s)
    return ' ' * (t // 2) + s + ' ' * (t - t // 2)


def red(s):
    return f'\033[31m{s}\033[0m'


def invert(s):
    return f'\033[7m{s}\033[0m'
