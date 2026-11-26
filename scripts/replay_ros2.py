"""Publish recorded ReachBench sensor data to ROS 2 with original episode timestamps."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import rclpy
from rclpy.duration import Duration
from sensor_msgs.msg import Image, JointState


def stamp(header, t):
    header.stamp.sec, header.stamp.nanosec = divmod(round(t * 1e9), 10**9)


def image_message(array, encoding, camera, t):
    msg = Image()
    stamp(msg.header, t)
    msg.header.frame_id = camera + '_camera_optical_frame'
    msg.height, msg.width = array.shape[:2]
    msg.encoding = encoding
    msg.step = array.nbytes // msg.height
    msg.is_bigendian = 0
    msg.data = array.tobytes(order='C')
    return msg


def publish(folder, speed):
    record = json.loads((folder / 'run.json').read_text())
    node = rclpy.create_node('reachbench_replay')
    try:
        rgb = node.create_publisher(Image, '/reachbench/rgb', 10)
        depth = node.create_publisher(Image, '/reachbench/depth', 10)
        joints = node.create_publisher(JointState, '/reachbench/joint_states', 100)
        end = time.monotonic() + 30
        while not all(p.get_subscription_count() for p in (joints, rgb, depth)):
            if time.monotonic() > end:
                raise RuntimeError('Subscribe to all three topics before starting replay.')
            rclpy.spin_once(node, timeout_sec=0.05)
        events = [(r['t'], 'state', r) for r in record['trace']]
        events.extend((r['t'], 'image', r) for r in record['sensors'])
        start = time.monotonic()
        for t, kind, row in sorted(events, key=lambda event: event[0]):
            time.sleep(max(0, start + t / speed - time.monotonic()))
            if kind == 'state':
                state = JointState()
                stamp(state.header, t)
                state.name = [f'joint{i}' for i in range(1, 8)] + ['finger_joint1', 'finger_joint2']
                state.position = row['qpos'][:9]
                joints.publish(state)
            else:
                with np.load(folder / row['rgbd']) as frame:
                    rgb.publish(image_message(frame['rgb'], 'rgb8', row['camera'], t))
                    depth.publish(image_message(frame['depth'].astype('<f4'), '32FC1', row['camera'], t))
        for publisher in (rgb, depth, joints):
            if not publisher.wait_for_all_acked(Duration(seconds=5)):
                raise RuntimeError('Timed out waiting for ROS 2 delivery.')
    finally:
        node.destroy_node()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--speed', type=float, default=1)
    args = parser.parse_args()
    if not np.isfinite(args.speed) or args.speed <= 0:
        parser.error('--speed must be finite and greater than zero')
    rclpy.init()
    try:
        publish(args.folder, args.speed)
    finally:
        rclpy.shutdown()
