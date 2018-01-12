import re

# Default parse scheme for current files on DriveOne
def default_parse(filename):

    depth_regexp = '([lr]t[0-9]d|[LR]T[0-9]D)([-.0-9]+)F([0-9]+)'
    depth = re.match(depth_regexp, filename)
    if depth is not None:
        return (depth.group(2), depth.group(3))
    return (None, None)
