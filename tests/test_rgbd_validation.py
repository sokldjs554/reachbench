"""Normal and rejected inputs are separate tests; no simulation is required."""
import numpy as np
import pytest

from manipulation.check_rgbd import inspect_rgbd


def test_valid_depth_ratio_includes_boundaries_and_nonfinite_values(tmp_path, capsys):
    rgb = np.zeros((2, 4, 3), dtype=np.uint8)
    depth = np.array([[0.5, 1.0, 2.0, 2.9], [0.0, 3.0, np.nan, np.inf]])
    path = tmp_path / "mixed.npz"
    np.savez(path, rgb=rgb, depth=depth)

    inspect_rgbd(path)

    assert capsys.readouterr().out == (
        "이미지 크기 (너비 x 높이): 4 x 2\n"
        "유효 깊이 비율: 50.00%\n"
    )


def test_mismatched_image_sizes_raise_before_reporting_a_ratio(tmp_path, capsys):
    path = tmp_path / "mismatch.npz"
    np.savez(path, rgb=np.zeros((2, 2, 3), dtype=np.uint8), depth=np.ones((2, 4)))

    with pytest.raises(ValueError, match="이미지 크기가 다릅니다"):
        inspect_rgbd(path)

    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("rgb_shape, depth_shape", [
    ((2, 4), (2, 4)),
    ((2, 4, 4), (2, 4)),
    ((2, 4, 3), (2, 4, 1)),
])
def test_invalid_image_layouts_raise(tmp_path, rgb_shape, depth_shape):
    path = tmp_path / "layout.npz"
    np.savez(path, rgb=np.zeros(rgb_shape, dtype=np.uint8), depth=np.ones(depth_shape))

    with pytest.raises(ValueError, match="이미지 형식을 확인하세요"):
        inspect_rgbd(path)


def test_empty_image_is_rejected_without_mean_of_empty_array(tmp_path):
    path = tmp_path / "empty.npz"
    np.savez(path, rgb=np.zeros((0, 4, 3), dtype=np.uint8), depth=np.empty((0, 4)))

    with pytest.raises(ValueError, match="깊이 이미지에 픽셀이 없습니다"):
        inspect_rgbd(path)


@pytest.mark.parametrize("depth, expected", [
    (np.ones((2, 2)), "100.00%"),
    (np.array([[np.nan, np.inf], [0.0, 3.0]]), "0.00%"),
])
def test_all_valid_or_invalid_depth_is_reported(tmp_path, capsys, depth, expected):
    path = tmp_path / "depth.npz"
    np.savez(path, rgb=np.zeros((2, 2, 3), dtype=np.uint8), depth=depth)

    inspect_rgbd(path)

    assert f"유효 깊이 비율: {expected}" in capsys.readouterr().out
