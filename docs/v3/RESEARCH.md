# 공고 기준 재조사와 v3 설계

2026-11-17 KST. Codex가 18개 저장소 README, 관련 코드, 접근 가능한 공개 데모·영상 구간을 조사했다. 아래는 직접 확인한 범위이며 다른 작성자의 실험을 재현한 것은 아니다.

[채용 원문](https://www.wanted.co.kr/wd/381292)의 Physical AI 인식·판단·행동, 시뮬레이션, 센서 위치 인식, 제어 연계, 데이터 파이프라인을 기준으로 과제를 선정했다. [회사 HABILIS Brain 공개 시연](https://tommoro-ai.github.io/habilis_brain_0_web/)의 물체 위치 변화 후 복구는 문제 선정의 참고다. 회사의 학습된 조작 능력을 재현했다는 주장은 하지 않는다. 자격요건 원문과 회사 공식 채용 페이지의 구분은 [최초 공고 조사](../RESEARCH.md)에 보존했다.

기존 ReachBench는 평면 접근·충돌 질의·병진 보정 실험이다. 이번에는 7자유도 Panda, 자유 물체, 모터 추종과 접촉 집기, 추가 카메라 관측을 구현했다. GPU 없이 Python CPU에서 평가하고 동일 MuJoCo 버전의 WASM으로 공개 직접 실행을 제공할 수 있어 선택했다. 색상과 레이아웃만 바꾸어 기존 평면 접근을 조작 실험으로 소개하지 않는다.

## [WorkCell C / GraspSight](https://github.com/ahmedsohail2003/workcell-partC-grasping)

- 확인: README, env·pipeline·executor 코드, 실제 7.3초 영상의 6개 시점
- 구성: MuJoCo SO-ARM100. RGB-D 역투영 → 보정된 외부 파라미터 → 평면 제거·군집화 → 큐브 x/y/yaw 추정 → 그리퍼로 집어 트레이에 놓기. env.step은 ctrl 설정 후 mj_step을 호출한다.
- 해석 한계: 작성자 보고 20/20. 알려진 24mm 큐브, 이상적인 depth, 제한된 테이블 작업. 한 번 관찰한 뒤 실행하므로 지속적 시각 피드백의 예는 아니다.
- 참고점: CPU 기반 조작 시스템의 최소 완성 범위와 간결한 실행 영상.
- [연결된 데모·자료](https://ahmedsohail2003.github.io/workcell/)

## [WorkCell A / ACT](https://github.com/ahmedsohail2003/workcell-partA-imitation)

- 확인: README, eval_policy.py, 사이트 재생 영상
- 구성: 스크립트 전문가 → LeRobot 시연 데이터 → ACT → 전면·손목 RGB와 관절 상태로 반복 추론. 학습 데이터와 다른 평가 seed, 시각/물리 랜덤화 비교.
- 해석 한계: 작성자 보고 ACT-DR 45/50, 특정 실패 지역을 더 수집한 dr2는 44/50. 복구 데이터가 ACT 성능을 낮춘 결과도 공개. 단일 학습 실행과 여러 변경 요인 때문에 원인 해석을 확정할 수 없다.
- 참고점: 데이터·정책·실패·재학습을 연결하는 가장 관련성 높은 개인 포트폴리오 참고.
- [연결된 데모·자료](https://ahmedsohail2003.github.io/workcell/)

## [WorkCell B / SmolVLA](https://github.com/ahmedsohail2003/workcell-partB-vla)

- 확인: README, 연결된 모델·노트북 경로, 사이트 재생 영상
- 구성: 450M SmolVLA에서 비전 언어 백본을 고정하고 행동 전문가를 학습. 같은 시뮬레이션에서 ACT와 비교.
- 해석 한계: 작성자 보고 동일한 20회 평가에서 0/20 → 11/20 → 18/20. T4 16GB, 약 8시간 학습을 기록. 한 과제·작은 평가 표본이며 원인 설명은 추가 통제가 필요하다.
- 참고점: GPU 확보 후 진행할 학습 확장. CPU 환경에서 이 결과를 그대로 약속할 수 없다.
- [연결된 데모·자료](https://ahmedsohail2003.github.io/workcell/)

## [UR5e + Robotiq](https://github.com/Sachin6120/ur5e-robotiq-pickplace)

- 확인: README, 소스 트리, m3_grasp.cpp 일부, D3 GIF 6개 시점
- 구성: ROS 2 Jazzy·Gazebo·MoveIt2. RGB-D 위치·yaw → 접근·그리퍼 닫기 → 들어올림·운반·놓기. 계획 장면과 접촉 판정의 역할을 구분한다.
- 해석 한계: 4개 회귀 사례는 광범위한 성공률 평가와 다르다. MoveIt PlanningScene attachment만 보고 물리적 강제 부착이라고 판단해서도 안 된다. 전체 시스템은 이번 조사에서 빌드하지 않았다.
- 참고점: 좌표계·그리퍼·계획·검증의 통합 설계 참고.
- [연결된 데모·자료](https://github.com/Sachin6120/ur5e-robotiq-pickplace/releases/tag/stage2-pose-generalization-pass)

## [Find the Viewpoint](https://github.com/S-SAMRINA/Find_the_viewpoint)

- 확인: README, 적응적 시점 탐색 GIF 6개 시점
- 구성: UR5e 손목 카메라로 기준 이미지와 유사한 관찰 위치 탐색. DINOv3+SIFT, CLIP, ORB 비교. IK·충돌·가시성 조건을 확인한다.
- 해석 한계: 시점 일치 과제이며 집기 복구 자체는 아니다. 방법별 score 척도가 달라 직접 비교할 수 없다. 저자가 실제 로봇 결과도 기록했으나 이번 조사에서 독립 재현하지 않았다.
- 참고점: 가림을 해결하기 위해 로봇이 어디를 보러 움직이는지 시각화하는 방식.
- [연결된 데모·자료](https://github.com/S-SAMRINA/Find_the_viewpoint#readme)

## [active_grasp](https://github.com/ethz-asl/active_grasp)

- 확인: README, nbv.py·controller.py 코드; 연결 영상 내용은 미검증
- 구성: Panda 손목 depth → TSDF 통합 → 가능한 시점들의 정보 이득 → 재관측 → 안정된 집기 예측에서 종료 → 그립 실행.
- 해석 한계: ROS Noetic·MoveIt·VGN 의존. 코드에서 view 수·이동 거리·탐색/집기 시간 기록을 확인. 이 논문 시스템 전체를 현재 환경에서 실행하지 않았다.
- 참고점: 가림 개선의 알고리즘 근거. 관찰 추가 비용과 종료 조건까지 평가해야 한다.
- [연결된 데모·자료](https://youtu.be/67W_VbSsAMQ)

## [Vision-based robotic arm](https://github.com/DiyaJabin/vision-based-robotic-arm)

- 확인: README, 96.4초 영상의 6개 시점
- 구성: PyBullet KUKA. HSV·YOLO·혼합 검출, 평면 위치 추정, 집기 후보와 IK. 합성 이미지 90장의 학습 범위를 기록.
- 해석 한계: 그리퍼 접촉 대신 시뮬레이션 제약으로 부착. 문서와 영상은 실패도 보여준다. 로봇 모델이 더 사실적이라고 검증 깊이가 자동으로 높아지는 것은 아니다.
- 참고점: 센서 패널과 실행 화면 구성은 참고하되 물리 집기 근거로 쓰지 않는다.
- [연결된 데모·자료](https://github.com/user-attachments/assets/0259cda2-13be-4e21-aad3-eadf54be0d34)

## [Robotic arm simulation](https://github.com/GKoutilya/robotic-arm-simulation)

- 확인: README
- 구성: PyBullet RGB-D 역투영·RRT·IK·ROS2 노드 분리.
- 해석 한계: 목표 분할에 시뮬레이터 segmentation ID를 쓰고 물체 부착에 constraint 및 시뮬레이터 상태를 사용한다고 명시. 학습된 비전 검출·접촉 기반 집기로 표현하면 안 된다.
- 참고점: 모듈 경계 참고. ReachBench의 픽셀 기반 인식을 정답 분할로 바꾸는 것은 개선이 아니다.
- [연결된 데모·자료](https://github.com/GKoutilya/robotic-arm-simulation#readme)

## [TeleOp-BC](https://github.com/cadenpage/TeleOp-BC)

- 확인: README, policy GIF 6개 시점
- 구성: 키보드/손 동작 시연 → 위치·속도·거리 3차원 상태 → 작은 MLP → 힘 제어.
- 해석 한계: 1차원 블록 과제. 로봇팔 비전 조작 사례로는 범위가 좁다.
- 참고점: 작게라도 시연 수집·학습·롤아웃을 실제 연결하는 방식.
- [연결된 데모·자료](https://github.com/cadenpage/TeleOp-BC#readme)

## [BC robot manipulation](https://github.com/AlvinOctaH/bc-robot-manipulation)

- 확인: README, 수집·평가 코드, GIF 6개 시점
- 구성: Robosuite Panda Lift. 스크립트 전문가·HDF5·MLP 행동 복제.
- 해석 한계: 평가 코드 use_camera_obs=False; cube_pos 등 상태 입력. 80%는 저자 20회 보고. 데이터 수와 노이즈를 같이 바꿔 증강만의 효과로 해석할 수 없다.
- 참고점: 학습 데이터 구조는 참고. 이미지 정책 또는 증강의 순수 효과로 소개하지 않는다.
- [연결된 데모·자료](https://github.com/AlvinOctaH/bc-robot-manipulation#readme)

## [Franka IL/RL](https://github.com/e-cagan/franka-il-rl)

- 확인: README 실험·환경·배포 절
- 구성: BC·DAgger·SAC 비교, 데이터 수·학습 seed, ONNX·ROS2 배포.
- 해석 한계: 실제 주 실험은 제목의 Franka가 아니라 FetchPickAndPlace. 상태 입력 정책. BC/DAgger는 3 seed×100회 보고; SAC는 단일 seed 탐색. TensorRT 로드 실패도 명시.
- 참고점: 실패한 RL과 추론 배포 선택을 숨기지 않는 실험 기록 방식.
- [연결된 데모·자료](https://github.com/e-cagan/franka-il-rl#readme)

## [Object pose estimation](https://github.com/noelkelias/object-pose-estimation)

- 확인: README
- 구성: RGB-D·색상 마스크·점군 중심점·ROS2 TF·지연 시간 측정.
- 해석 한계: 번들 데이터는 CPU 합성 데이터이며 외부 시뮬레이터 export는 별도. 중심 위치 추정은 완전한 6D pose가 아니다. 제어까지 이어지지 않는다.
- 참고점: 측정 구성 참고. 도구 이름과 실제 검증 범위를 구별하는 반면교사.
- [연결된 데모·자료](https://github.com/noelkelias/object-pose-estimation#readme)

## [ActLoc](https://github.com/cvg/ActLoc)

- 확인: README, 프로젝트 링크, 공개 데모 브라우저 접속
- 구성: 위치 인식에 유리한 카메라 방향 선택 연구.
- 해석 한계: 집기가 아닌 위치 인식 과제. 공개 데모는 조사 시점에 Runtime error: not enough hardware capacity. 학습/평가 일부 공개 상태에도 제한.
- 참고점: 실행 가능 여부를 별도로 확인해야 하는 사례. 정상 동작을 확인했다고 쓰지 않는다.
- [연결된 데모·자료](https://huggingface.co/spaces/Jeffreyli7012/ActLocDemo)

## [LLM Trajectory](https://github.com/Encrux/llm_trajectory)

- 확인: README, animator.ts, 브라우저 Play·실행 상태·Reset
- 구성: MuJoCo WASM·Three.js. 시뮬레이터 물체 좌표를 텍스트로 LLM에 전달 → 도구 호출 → 웨이포인트 → IK.
- 해석 한계: 카메라 비전이 아니다. 손을 열고 움직일 때 qpos 직접 설정, 물체를 잡은 동안 actuator 제어. 조사 환경에서 실행 시작과 Reset을 확인했지만 과제 완료는 확인하지 못했다.
- 참고점: 큰 3D 작업 공간·간단한 실행 조작·현재 행동 표시. LLM을 덧붙이는 것만으로 Physical AI 역량이 생기지 않는다.
- [연결된 데모·자료](https://llm-trajectory.boesch.dev/)

## [mjswan](https://github.com/ttktjmt/mjswan)

- 확인: README, 브라우저 G1 모델·정책 로드·Reset, 제어 입력 조사
- 구성: MuJoCo WASM + ONNX Runtime Web + Three.js. 학습 정책을 브라우저에서 추론하고 물리 시뮬레이션.
- 해석 한계: 시연 인프라와 학습 성과는 별개. 현재 ReachBench Python/PyBullet 코드를 자동 변환하는 도구가 아니다. 로딩에 시간이 필요했다.
- 참고점: 공개 정적 사이트에서도 기록 재생을 넘어 실제 정책 실행이 가능한 배포 구조.
- [연결된 데모·자료](https://ttktjmt.github.io/mjswan/)

## [mujoco_wasm](https://github.com/zalo/mujoco_wasm)

- 확인: README, 브라우저 Mug 모델 선택·시점 변경·Reset
- 구성: 브라우저 안의 MuJoCo 물리와 Three.js 시각화.
- 해석 한계: 물리 뷰어는 인식·학습 프로젝트 자체가 아니다. 모델 로딩과 상호작용을 별도로 검증해야 한다.
- 참고점: 실제 3D 시뮬레이션을 공개 데모로 제공하는 기술 참고.
- [연결된 데모·자료](https://zalo.github.io/mujoco_wasm/)

## [Pick-and-place arena](https://github.com/fabriziobattiloro/robotics-pick-and-place-arena)

- 확인: README
- 구성: Google AI Studio 예제 확장. 화면 JPEG → VLM 검출 → 3D raycast → IK·집기 순서. 모델별 검출 비교.
- 해석 한계: 외부 API 키가 필요. README가 현재 빌드의 client key 포함 문제를 명시하여 그대로 공개 배포할 수 없다. 독립적인 공개 실행은 확인하지 않았다.
- 참고점: 지시→인식→행동 구조 참고. 정확한 depth·정책 학습·배포 검증은 별도.
- [연결된 데모·자료](https://github.com/fabriziobattiloro/robotics-pick-and-place-arena#readme)

## [robomimic](https://github.com/ARISE-Initiative/robomimic)

- 확인: README 및 데이터·평가 문서 연결
- 구성: 시연 데이터, 상태/영상 관찰, action, 학습·검증 split, 롤아웃 평가를 위한 표준 연구 프레임워크.
- 해석 한계: 개인 포트폴리오와 동일 규모로 비교할 대상은 아니다. 프레임워크 도입 자체가 본인의 연구 기여도 아니다.
- 참고점: 자체 임의 포맷보다 재현 가능한 데이터·학습 평가 관례를 채택.
- [연결된 데모·자료](https://robomimic.github.io/)

## 이번 적용과 차이

- WorkCell: RGB-D → IK → 접촉 집기 → 놓기의 작은 완결 과제. 해당 코드·UI를 복제하지 않았다.
- active_grasp / Find the Viewpoint: 가림의 원인을 관찰에서 해결하는 방향. 이번 구현은 **두 고정 카메라를 선택**하며 정보 이득 기반 이동 시점 계획은 아니다.
- MuJoCo 웹 사례: 실제 WASM 물리 실행과 3D 화면을 결합하되 물체 정답 좌표를 인식 입력으로 사용하지 않는다.
- [RoboEval](https://robo-eval.github.io/index.html): 성공률과 실패 실행을 연결한다.
- [Foxglove](https://foxglove.dev/product/visualization): 시간축·관측·행동 기록을 연결한다. 상용 로그인 후 기능 전체를 검증한 것은 아니다.

브라우저는 Three.js로 RGB와 depth를 렌더링한다. Python은 MuJoCo EGL renderer다. 렌더러가 달라 픽셀·결과가 완전히 같다고 주장하지 않으며 Python 평가 수치를 라이브 실행 성과로 표시하지 않는다. 공개 모델 자산만 라이선스에 따라 사용했다. 학습 정책, ROS 2, 실기 검증은 수행하지 않았다.
