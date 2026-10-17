"""Frame-set oracle; deliberately has no RAM, lane-window or RTL scheduler model."""


def support3(points):
    """Image exterior is absent from points (zero padding); never create a hit."""
    return {(x, y) for x, y in points
            if sum((x + dx, y + dy) in points
                   for dy in (-1, 0, 1) for dx in (-1, 0, 1)) >= 3}


def words(points, width, height):
    for y in range(height):
        for x in range(0, width, 4):
            mask = sum(1 << (3 - lane) for lane in range(4) if (x + lane, y) in points)
            yield x, y, mask


def selfcheck():
    assert support3({(1, 1)}) == set()
    assert support3({(1, 1), (2, 1)}) == set()
    assert support3({(1, 1), (2, 1), (3, 1)}) == {(2, 1)}
    assert support3({(1, 1), (1, 2), (1, 3)}) == {(1, 2)}
    assert support3({(1, 1), (2, 2), (3, 3)}) == {(2, 2)}
    block = {(0, 0), (1, 0), (0, 1), (1, 1)}
    assert support3(block) == block  # cluster counterexample must remain
    assert list(words({(0, 0), (3, 0)}, 4, 1)) == [(0, 0, 9)]
