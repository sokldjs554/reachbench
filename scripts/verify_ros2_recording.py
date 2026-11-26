"""Check bag payloads, order, frames and timestamps against the original episode."""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image, JointState


def verify(folder, bag):
    record = json.loads((folder / 'run.json').read_text())
    rgb, depth, joints = ('/reachbench/' + name for name in ('rgb', 'depth', 'joint_states'))
    expected = {rgb: record['sensors'], depth: record['sensors'], joints: record['trace']}
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(bag), storage_id='sqlite3'),
                rosbag2_py.ConverterOptions('', ''))
    counts = Counter()
    while reader.has_next():
        topic, data, _ = reader.read_next()
        row = expected[topic][counts[topic]]
        counts[topic] += 1
        msg = deserialize_message(data, JointState if topic == joints else Image)
        assert msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec == round(row['t'] * 1e9)
        if topic == joints:
            assert list(msg.name) == [f'joint{i}' for i in range(1, 8)] + ['finger_joint1', 'finger_joint2']
            np.testing.assert_array_equal(msg.position, row['qpos'][:9])
        else:
            assert msg.header.frame_id == row['camera'] + '_camera_optical_frame'
            with np.load(folder / row['rgbd']) as frame:
                original = frame['rgb'] if topic == rgb else frame['depth'].astype('<f4')
                assert (msg.height, msg.width) == original.shape[:2]
                assert msg.encoding == ('rgb8' if topic == rgb else '32FC1')
                assert msg.step == original.nbytes // original.shape[0] and msg.is_bigendian == 0
                assert bytes(msg.data) == original.tobytes()
    assert counts == {topic: len(rows) for topic, rows in expected.items()}
    return dict(counts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('bag', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.folder, args.bag), sort_keys=True))
