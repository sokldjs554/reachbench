# ReachBench · Vision to Motion

[GitHub 저장소](https://github.com/sokldjs554/reachbench) · [배포 데모](https://reachbench-vision-control.ykh13571.chatgpt.site) · [실험 결과](docs/RESULTS.md) · [공고 조사](docs/RESEARCH.md)

데모는 현재 Sites 소유자 전용입니다. 공개 저장소를 내려받으면 로컬에서 모든 기록을 탐색하고 새로운 장면을 실행할 수 있습니다.

RGB 카메라로 작업물과 장애물을 찾고, 2관절 평면 로봇팔의 접근 궤적을 비교하는 **CPU 기구학 시뮬레이션 실험**. 투모로로보틱스 Physical AI / Robotics R&D 인턴 직무의 인식→공간 추정→경로→평가 연결을 보여주는 독립 프로젝트다.

**실물 로봇·학습 모델·파지·보행·Whole-body Control 결과가 아니다.** Codex가 조사·설계·구현·실험·문서화를 수행했다. 지원자의 독자 개발 경험으로 기재하지 말 것. [기여와 면접 안내](docs/INTERVIEW.md)를 먼저 확인한다.

## 실제 평가 결과

20개 seed × 5개 조건 × 4개 방법, 총 400회 CPU 시뮬레이션을 실행했습니다. 성공 기준은 실행 중 장애물 충돌이 없고 최종 목표 XY 오차가 35 mm 이내인 경우입니다.

| 방법 | 성공 / 전체 |
|---|---:|
| RGB + 직접 접근 | 2 / 100 |
| HSV + 직접 접근 | 3 / 100 |
| RGB + A* | 39 / 100 |
| HSV + A* | 59 / 100 |

개선 방법은 기본·어두운 조명에서 각각 20/20, 추가 장애물에서 19/20을 성공했습니다. 목표 가림과 보정 오차에서는 모두 실패했습니다. 이 수치는 구성한 합성 장면의 결과이며 실제 로봇의 성능이 아닙니다.

## 빠르게 체험

Python 3.11 권장. GPU·디스플레이·계정·모델 키가 필요 없다.

```bash
git clone https://github.com/sokldjs554/reachbench.git
cd reachbench
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m reachbench.serve
```

http://127.0.0.1:8000 에서 장면·조건 변경, 기준/개선 경로 동시 재생, 시간 탐색, 카메라 검출 오버레이, 기록 다운로드가 가능하다. **새로운 장면 직접 실행**을 열면 목표 X/Y를 바꾸어 같은 Python 엔진으로 새 계산을 수행한다. 로컬 서버는 localhost에만 바인딩하고 순차 처리한다. 외부 공개 API 용도로 설계하지 않았다.

Windows는 `.venv\Scripts\activate`로 활성화한다. Python 3.12 환경에서는 PyBullet wheel이 없어 소스 빌드가 시도될 수 있다. 이번 실행은 Python 3.11.18 + Linux x86_64에서 완료했다. 다른 OS는 검증하지 않았다.

웹 배포판은 **사전에 실행한 시뮬레이션의 인터랙티브 재생기**다. 브라우저에서 PyBullet을 새로 실행하지 않는다. 새 계산은 로컬 서버에서만 지원한다. 정적 배포는 `dist/`를 게시하면 된다. Sites 배포는 기본 소유자 전용 접근이며 외부 면접관에게 전달하기 전 접근 설정을 확인해야 한다.

## 재현

```bash
python -m pytest -q
python -m reachbench.evaluate --start 1000 --count 20 --out dist/data
python -m reachbench.export
python -m reachbench.audit
python -m pytest -q
```

100개 장면(20 seed × 5 조건) × 4 방법 = 400회. 평가 설정은 실행 전에 `dist/data/config.json`에 저장된다. 기존 결과를 보존하려면 저장소 복사본에서 재실행한다. 타이밍을 제외한 결과·궤적은 고정 seed와 고정 버전으로 재현하는 것을 목표로 한다. 플랫폼 간 픽셀·부동소수점 차이는 발생할 수 있다.

`export`는 중복된 RGB 입력을 장면별 하나로 합치며 재인코딩하지 않는다. `audit`는 이미지 형태·에피소드 ID·시간 순서·유한 관절값·집계를 확인하고 SHA-256 목록을 만든다. 누락/실패 에피소드를 평가에서 삭제하지 않는다. 학습/검증 분할이나 데이터 기반 임계값 학습은 수행하지 않았다. 개발용 seed 0–9 및 100은 구현 디버깅에 사용했으며 평가 seed는 1000–1019다.

## 구조

- `reachbench/sim.py`: 생성 장면, PyBullet 렌더러/충돌, RGB/HSV 인식, 카메라 역투영, FK/IK, A*와 경로 실행
- `reachbench/evaluate.py`: paired 2×2 실험, Wilson 구간, 처리 시간, 실패 집계
- `reachbench/serve.py`: 로컬 UI와 새로운 장면 계산
- `reachbench/export.py`, `reachbench/audit.py`: 데이터 중복 정리와 무결성 검사
- `tests/test_core.py`: 기하·충돌·재현성·평가 산식 및 전수 기록 검증
- `dist/`: 배포 가능한 정적 데모, 실제 입력 PNG, 실행별 JSON, CSV, 집계, 실험 보고서
- `docs/RESEARCH.md`: 공고 원문·회사 연결·대안 비교·도구 선택
- `docs/EXPERIMENT.md`: 수식·설정·결과·실패·한계
- `docs/INTERVIEW.md`: 기여 구분, 직접 수행 체크포인트, 질문과 답변
- `docs/THIRD_PARTY.md`: 라이선스·사용 범위

## 데모 안내

기본 조명에서 두 경로를 재생 → 어두운 조명에서 검출 차이 → 가림에서 이동 보류 → 보정 오차에서 실패 원인 확인 → 평가 결과 탭에서 네 방법과 조건별 집계 확인. 평면도는 저장된 실제 관절값을 SVG로 그린 것이며 물리 시뮬레이터의 실시간 영상이 아니다. 카메라 입력·스냅샷은 PyBullet이 실제 생성한 이미지다.

설계는 Foxglove/Rerun의 기록·공간·센서 탐색 흐름을 참고했다. 전체 화면 렌더링·모바일 브라우저 검증은 현재 환경에서 지원되는 `cua_repl.js`가 없어 수행하지 못했다. DOM 인터랙션과 데이터 연결은 별도 자동 검사했다. 외부 사용자의 사용성 테스트는 수행하지 않았다.
