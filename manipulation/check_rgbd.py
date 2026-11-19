import numpy as np


def depth_quality(path):
    """Validate a recorded RGB-D frame and count usable depth samples."""
    with np.load(path, allow_pickle=False) as frame:
        rgb = frame["rgb"]
        depth = frame["depth"]

    if depth.ndim != 2 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"이미지 형식을 확인하세요. rgb={rgb.shape}, depth={depth.shape}")
    if rgb.shape[:2] != depth.shape:
        raise ValueError(f"이미지 크기가 다릅니다. rgb={rgb.shape[:2]}, depth={depth.shape}")
    if depth.size == 0:
        raise ValueError("깊이 이미지에 픽셀이 없습니다.")

    height, width = depth.shape
    valid = np.isfinite(depth) & (depth > 0) & (depth < 3)
    return {
        "height": height,
        "width": width,
        "valid_depth_pixels": int(valid.sum()),
        "total_pixels": depth.size,
    }


def inspect_rgbd(path):
    quality = depth_quality(path)
    width, height = quality["width"], quality["height"]
    ratio = quality["valid_depth_pixels"] / quality["total_pixels"]
    print(f"이미지 크기 (너비 x 높이): {width} x {height}")
    print(f"유효 깊이 비율: {ratio:.2%}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RGB-D 크기 및 유효 깊이 비율 검사")
    parser.add_argument("path", help="rgb와 depth 배열을 포함한 NPZ 파일")
    inspect_rgbd(parser.parse_args().path)
