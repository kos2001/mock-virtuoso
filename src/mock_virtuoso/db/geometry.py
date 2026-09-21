"""좌표와 변환. DBU 격자 반올림은 하지 않는다 (스펙 §2 비목표)."""

from __future__ import annotations

ORIENTS = ("R0", "R90", "R180", "R270", "MX", "MY", "MXR90", "MYR90")

# 각 orient를 (x, y) -> (x', y') 선형 변환으로 표현한다.
_MATRIX = {
    "R0":    (1.0, 0.0, 0.0, 1.0),
    "R90":   (0.0, -1.0, 1.0, 0.0),
    "R180":  (-1.0, 0.0, 0.0, -1.0),
    "R270":  (0.0, 1.0, -1.0, 0.0),
    "MX":    (1.0, 0.0, 0.0, -1.0),
    "MY":    (-1.0, 0.0, 0.0, 1.0),
    "MXR90": (0.0, 1.0, 1.0, 0.0),
    "MYR90": (0.0, -1.0, -1.0, 0.0),
}


def transform_point(point, offset, orient: str) -> list[float]:
    try:
        a, b, c, d = _MATRIX[orient]
    except KeyError:
        raise ValueError(f"unknown orientation: {orient}") from None
    x, y = float(point[0]), float(point[1])
    return [a * x + b * y + float(offset[0]), c * x + d * y + float(offset[1])]


def _normalize(corners) -> list[list[float]]:
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return [[min(xs), min(ys)], [max(xs), max(ys)]]


def transform_bbox(bbox, offset, orient: str) -> list[list[float]]:
    (llx, lly), (urx, ury) = bbox[0], bbox[1]
    corners = [
        transform_point((llx, lly), offset, orient),
        transform_point((urx, lly), offset, orient),
        transform_point((urx, ury), offset, orient),
        transform_point((llx, ury), offset, orient),
    ]
    return _normalize(corners)


def bbox_of_points(points) -> list[list[float]]:
    pts = [(float(p[0]), float(p[1])) for p in points]
    if not pts:
        return [[0.0, 0.0], [0.0, 0.0]]
    return _normalize(pts)


def bbox_of_path(points, width: float) -> list[list[float]]:
    w = float(width)
    if w < 0.0:
        raise ValueError(f"negative path width: {w}")
    if not points:
        raise ValueError("empty point list")
    box = bbox_of_points(points)
    half = w / 2.0
    return [[box[0][0] - half, box[0][1] - half],
            [box[1][0] + half, box[1][1] + half]]
