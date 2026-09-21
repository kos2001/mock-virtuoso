import pytest

from mock_virtuoso.db.geometry import (
    ORIENTS,
    bbox_of_path,
    bbox_of_points,
    transform_bbox,
    transform_point,
)


def test_r0_is_translation_only():
    assert transform_point((1.0, 2.0), (10.0, 20.0), "R0") == [11.0, 22.0]


def test_r90_rotates_counterclockwise():
    assert transform_point((1.0, 0.0), (0.0, 0.0), "R90") == [0.0, 1.0]


def test_r180():
    assert transform_point((1.0, 2.0), (0.0, 0.0), "R180") == [-1.0, -2.0]


def test_r270():
    assert transform_point((1.0, 0.0), (0.0, 0.0), "R270") == [0.0, -1.0]


def test_mx_mirrors_about_x_axis():
    assert transform_point((1.0, 2.0), (0.0, 0.0), "MX") == [1.0, -2.0]


def test_my_mirrors_about_y_axis():
    assert transform_point((1.0, 2.0), (0.0, 0.0), "MY") == [-1.0, 2.0]


def test_all_orients_supported():
    for orient in ORIENTS:
        transform_point((1.0, 1.0), (0.0, 0.0), orient)


def test_unknown_orient_raises():
    with pytest.raises(ValueError):
        transform_point((0.0, 0.0), (0.0, 0.0), "R45")


def test_transform_bbox_normalizes_corners():
    # R180은 코너를 뒤집으므로 결과가 정규화되어야 한다.
    result = transform_bbox([[0.0, 0.0], [2.0, 1.0]], (0.0, 0.0), "R180")
    assert result == [[-2.0, -1.0], [0.0, 0.0]]


def test_bbox_of_points():
    assert bbox_of_points([(1.0, 5.0), (3.0, 2.0), (-1.0, 4.0)]) \
        == [[-1.0, 2.0], [3.0, 5.0]]


def test_bbox_of_path_expands_by_half_width():
    assert bbox_of_path([(0.0, 0.0), (4.0, 0.0)], 2.0) \
        == [[-1.0, -1.0], [5.0, 1.0]]
