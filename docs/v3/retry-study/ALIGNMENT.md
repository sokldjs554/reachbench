# 카메라 관측과 로봇 상태·명령의 시간 정렬

42회 실행의 카메라 관측 86개를 한 줄에 하나씩 저장했다. 각 행에는 실제 RGB-D 파일 경로, 목표의 추정 XY, 관측 시각까지 기록된 마지막 팔·손가락 상태, 관측 후 처음 기록된 모터 명령이 있다. RGB-D 관측은 제어기가 재관측을 요청할 때만 생기고 관절 기록은 대체로 40 ms 간격으로 남는다.

[86행 JSONL](../../../dist/retry/observations.jsonl) · [시뮬레이션 원본](records.tar.gz) · [생성 코드](../../../scripts/export_retry_alignment.py)

## 시간 규칙

모든 시각은 실행 시작 기준 시뮬레이션 초다. 한 실행 내부에서만 대응시키며 같은 시각에 서로 다른 카메라가 관측했다면 두 행을 유지한다.

| 필드 | 산출 방법 |
|---|---|
| 관측 시각 `t` | 원본 `sensors[i].t` |
| 상태 시각 `state_t` | `trace.t ≤ t`를 만족하는 마지막 샘플. 같은 시각의 중복 기록은 원본 순서에서 마지막 행 선택 |
| `state_lag_ms` | 관측과 상태 사이의 차이(ms). 원본 시각 정밀도 1 ms |
| 다음 명령 `next_t` | `trace.t > t`를 만족하는 첫 샘플. 이후 기록이 없으면 `next_recorded_command`는 null |
| `next_phase`, `next_ctrl` | 해당 샘플의 단계와 모터 목표. 이미 입력된 목표를 유지하는 경우도 포함 |

실제 분포는 시각 일치 42행, 20 ms 차이 43행, 30 ms 차이 1행이었다. 예를 들어 seed 107 재시도 실행의 후면 관측은 6.61초에 이루어졌다. 직전 상태는 6.58초로 손가락 간격 69.926 mm였고, 다음 모터 기록은 6.62초 `approach` 단계의 그리퍼 명령 255였다. 상태와 명령 사이에 실행된 개별 물리 스텝은 이 해상도로 복원할 수 없다.

## 행 구조

- `sample_id`는 장면·재시도 설정·관측 번호를 합친 고유 키다. `group`은 같은 조건과 seed를 묶는다. 켬/끔 쌍과 같은 실행 내 관측을 후속 학습·평가에서 서로 다른 쪽으로 분할하면 장면이 중복된다.
- `split=case`는 기존 실패 사례 seed 107이고, `split=evaluation`은 평가 seed 200–219다. 이번 내보내기는 원래 평가 구분을 유지한다.
- `source`의 기록·NPZ·JPEG 경로는 원본 압축 파일을 푼 `work/retry-study/` 기준이다. `observation_index`는 `run.json`의 센서 배열 인덱스다. NPZ에는 무손실 RGB, m 단위 depth, 가상 카메라 파라미터가 있다.
- `observation`은 카메라, 시각과 픽셀에서 추정한 XY(m)를 담는다. 미검출이면 XY는 null이다. `state`에는 팔 관절 7개(rad), 양쪽 손가락 위치(m), 합산 간격(mm)만 담는다. 원본 시뮬레이터의 물체 정답 자세와 관측 오차는 이 행에서 제외했다.
- `next_recorded_command.next_ctrl`은 관절 위치 목표 7개(rad)와 그리퍼 목표 1개(닫기 0, 열기 255)다. 미래 모터 명령은 예측 대상이므로 관측 시점 입력과 분리한다.
- `quality`에는 이미지 크기와 유효 깊이 픽셀 수, 전체 픽셀 수가 있다. 유효 조건은 유한한 깊이면서 `0 < depth < 3 m`이다. 이 도구는 크기가 다르거나 빈 배열, 관절 기록 범위 밖의 관측, 누락된 설정 쌍을 거부한다. 개별 픽셀이 거리 범위를 벗어나도 해당 실행을 보존한다.

성공 기록과 실패 기록을 함께 보존했다. 이 자료의 용도는 관측과 기록된 행동을 같은 시간축에서 조회하는 것이다. 모델 학습이나 데이터 증강 효과 평가는 수행하지 않았다.

## 재생성

저장소 루트에서 [원본 확인과 압축 해제](README.md)를 마친 뒤 NumPy가 설치된 Python 환경에서 실행한다.

```bash
python -m scripts.export_retry_alignment work/retry-archive/work/retry-study work/rebuilt-alignment
cmp dist/retry/observations.jsonl work/rebuilt-alignment/observations.jsonl
cmp dist/retry/study.json work/rebuilt-alignment/study.json
python -m pytest -q tests/test_retry_alignment.py
```

`study.json`에는 seed 107 비교에 필요한 관측·이벤트·결과와 20쌍의 평가 집계를 담았다. `sensors/`는 해당 켬/끔 원본 실행에서 복사한 JPEG다. JSONL을 확인하거나 재집계하는 데 시뮬레이션 재실행은 필요하지 않다.
