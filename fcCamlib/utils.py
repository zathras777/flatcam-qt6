import logging

from numpy import ceil, cos, pi, sin, sqrt


def setup_log(name:str) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    # log.setLevel(logging.WARNING)
    # log.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def arc(center, radius, start, stop, direction, steps_per_circ):
    """
    Creates a list of point along the specified arc.

    :param center: Coordinates of the center [x, y]
    :type center: list
    :param radius: Radius of the arc.
    :type radius: float
    :param start: Starting angle in radians
    :type start: float
    :param stop: End angle in radians
    :type stop: float
    :param direction: Orientation of the arc, "CW" or "CCW"
    :type direction: string
    :param steps_per_circ: Number of straight line segments to
        represent a circle.
    :type steps_per_circ: int
    :return: The desired arc, as list of tuples
    :rtype: list
    """
    # TODO: Resolution should be established by maximum error from the exact arc.

    da_sign = {"cw": -1.0, "ccw": 1.0}
    points = []
    if direction == "ccw" and stop <= start:
        stop += 2 * pi
    if direction == "cw" and stop >= start:
        stop -= 2 * pi
    
    angle = abs(stop - start)
        
    #angle = stop-start
    steps = max([int(ceil(angle / (2 * pi) * steps_per_circ)), 2])
    delta_angle = da_sign[direction] * angle * 1.0 / steps
    for i in range(steps + 1):
        theta = start + delta_angle * i
        points.append((center[0] + radius * cos(theta), center[1] + radius * sin(theta)))
    return points


def autolist(obj):
    try:
        _ = iter(obj)
        return obj
    except TypeError:
        return [obj]


def distance(pt1, pt2):
    return sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)
