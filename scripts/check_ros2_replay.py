"""Capture a live replay in a new bag and verify every message against its input."""
import argparse
import signal
import subprocess
import sys
from pathlib import Path

from scripts.verify_ros2_recording import verify


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('bag', type=Path)
    args = parser.parse_args()
    if args.bag.exists():
        parser.error('choose a new output directory for the bag')
    recorder = subprocess.Popen(['ros2', 'bag', 'record', '-s', 'sqlite3', '-o', str(args.bag),
                                 '--topics', '/reachbench/rgb', '/reachbench/depth', '/reachbench/joint_states'])
    try:
        subprocess.run([sys.executable, '-m', 'scripts.replay_ros2', str(args.folder), '--speed', '4'],
                       check=True, timeout=90)
    finally:
        if recorder.poll() is None:
            recorder.send_signal(signal.SIGINT)
        try:
            recorder.wait(timeout=15)
        except subprocess.TimeoutExpired:
            recorder.kill()
            recorder.wait()
            raise
    print(verify(args.folder, args.bag))
