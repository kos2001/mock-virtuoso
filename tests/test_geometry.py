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
    # Verify each orientation against known expected results.
    # Uses (1,0) and (0,1) test points to fully distinguish all eight orientations.
    expected = {
        "R0":    {(1.0, 0.0): [1.0, 0.0], (0.0, 1.0): [0.0, 1.0]},
        "R90":   {(1.0, 0.0): [0.0, 1.0], (0.0, 1.0): [-1.0, 0.0]},
        "R180":  {(1.0, 0.0): [-1.0, 0.0], (0.0, 1.0): [0.0, -1.0]},
        "R270":  {(1.0, 0.0): [0.0, -1.0], (0.0, 1.0): [1.0, 0.0]},
        "MX":    {(1.0, 0.0): [1.0, 0.0], (0.0, 1.0): [0.0, -1.0]},
        "MY":    {(1.0, 0.0): [-1.0, 0.0], (0.0, 1.0): [0.0, 1.0]},
        "MXR90": {(1.0, 0.0): [0.0, 1.0], (0.0, 1.0): [1.0, 0.0]},
        "MYR90": {(1.0, 0.0): [0.0, -1.0], (0.0, 1.0): [-1.0, 0.0]},
    }
    for orient in ORIENTS:
        for point, expected_result in expected[orient].items():
            assert transform_point(point, (0.0, 0.0), orient) == expected_result


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


def test_bbox_of_path_negative_width_raises():
    # Negative path width is meaningless in layout. Raise loudly.
    with pytest.raises(ValueError):
        bbox_of_path([(0.0, 0.0), (2.0, 0.0)], -2.0)


def test_bbox_of_path_empty_points_raises():
    # Empty path is malformed input. Raise loudly, not return a plausible box.
    with pytest.raises(ValueError):
        bbox_of_path([], 2.0)


def test_bbox_of_path_zero_width_is_legal():
    # Zero width is a degenerate but meaningful centreline.
    assert bbox_of_path([(0.0, 0.0), (4.0, 0.0)], 0.0) \
        == [[0.0, 0.0], [4.0, 0.0]]


def test_bbox_of_points_empty_returns_zero_box():
    # Empty shape set is a normal state (e.g., cellview with no shapes yet).
    # Documents intentional difference from bbox_of_path([]).
    assert bbox_of_points([]) == [[0.0, 0.0], [0.0, 0.0]]
