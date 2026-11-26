# ROS 2에서 seed 107 센서 기록 재생

재시도 켬 실행의 RGB·깊이 영상과 관절 상태를 ROS 2 표준 메시지로 전송했다. 독립 프로세스의 `ros2 bag record`로 수신한 후 원본과 대조했다. 녹화 파일은 [seed 107 ROS 2 bag](seed107-bag.zip)에서 내려받을 수 있다.

| 토픽 | 메시지 | 원본과 대조한 내용 | 수신 |
|---|---|---|---:|
| `/reachbench/rgb` | sensor_msgs/Image, rgb8 | RGB 224 × 224 픽셀 전체 | 4 |
| `/reachbench/depth` | sensor_msgs/Image, 32FC1 | m 단위 깊이, float32 바이트 전체 | 4 |
| `/reachbench/joint_states` | sensor_msgs/JointState | 팔 7축(rad)·손가락 2축(m)의 이름과 위치 | 441 |

카메라 촬영 시각은 0.00, 1.96, 6.61, 8.16초이며 각 메시지의 header에는 원래의 시뮬레이션 시각이 있다. 카메라 프레임 이름으로 정면과 후면을 구분한다. 관절 상태는 원본의 별도 시각을 사용한다. 저장한 bag은 4배속 전송을 수신한 파일이므로 bag 자체의 수신 시간과 header의 실험 시간은 다르다.

Codex가 공식 ROS 2 Jazzy 컨테이너에서 발행·구독·녹화·원본 대조를 수행했다. ROS 토픽은 과거의 시뮬레이션 센서 기록을 전달하며 액추에이터 명령, 실시간 실기체 제어, TF 보정은 포함하지 않는다.

## 공개 bag 재생

ROS 2 Jazzy와 rosbag2가 설치된 셸에서 저장소 루트를 기준으로 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
unzip docs/v3/ros2/seed107-bag.zip -d work/ros2
ros2 bag info work/ros2/seed107-final
ros2 bag play work/ros2/seed107-final
```

## 원본으로 다시 녹화

[42회 기록 압축 해제](../retry-study/README.md#원본-확인과-재집계) 후 Linux에서 다음과 같이 실행한다. Ubuntu의 ROS 2 Python과 NumPy를 사용한다. 검증 명령은 세 토픽을 구독하는 recorder를 별도 프로세스로 시작하고, 발행한 메시지가 수신되면 bag을 닫고 검사한다. 출력 경로는 새 디렉터리여야 한다.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=41
python3 -m scripts.check_ros2_replay work/retry-archive/work/retry-study/seed107-on work/my-seed107-bag
```

발행 시각, 순서, 누락, 토픽별 개수, 카메라 프레임, 영상 크기·인코딩, 관절 위치 및 RGB·깊이 데이터가 원본과 일치하는지 검사한다. 검증 환경은 Docker 공식 이미지 `ros:jazzy-ros-base`(digest `sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6`)다. [발행 코드](../../../scripts/replay_ros2.py) · [메시지 검증](../../../scripts/verify_ros2_recording.py)
