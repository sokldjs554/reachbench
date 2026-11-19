# 첫 집기를 놓친 뒤 다시 시도하면 배치 결과가 달라지는가?

같은 위치 변화 장면에서 접근 후 재관측을 두 설정 모두에 유지하고, 빈 집기 후 한 번 더 관측해 집을 기회만 끄고 켰다. 알려진 실패 사례와 별도 평가 장면의 결과를 아래에 각각 표시한다.

| 장면 | 재시도 설정 | 배치 성공 | 실제 재시도 횟수 합계 | 평균 관측 횟수 | 평균 물체–트레이 XY 거리 | 평균 시뮬레이션 시간 | 평균 벽시계 시간 |
|---|---|---:|---:|---:|---:|---:|---:|
| 기존 실패 사례 107 | 끔 | 0/1 | 0 | 2 | 72.980 mm | 6.31 s | 4368.1 ms |
| 기존 실패 사례 107 | 켬 | 1/1 | 1 | 4 | 2.288 mm | 17.56 s | 2981.1 ms |
| 평가 200–219 | 끔 | 20/20 | 0 | 2 | 2.707 mm | 11.36 s | 1954.9 ms |
| 평가 200–219 | 켬 | 20/20 | 0 | 2 | 2.707 mm | 11.36 s | 1984.8 ms |

seed 107에서 두 실행 모두 첫 집기 확인 시점(6.31초)의 손가락 간격이 0.023 mm였다. 재시도를 끄면 그 자리에서 종료했다. 켜면 다시 관측하고 집어 12.51초에 간격 43.869 mm를 기록했고, 트레이에 물체를 놓은 뒤 배치 판정을 통과했다. 두 실행의 11.25초 차이에는 운반·놓기·후퇴까지 포함된다.

평가 20쌍은 모두 첫 집기를 통과했다. 같은 seed에서 재시도 설정에 따른 성공률 차이는 0%p였고, 저장된 관절 상태·모터 명령·단계 기록도 쌍마다 같았다. 42회 모두 로봇–가림판 접촉은 0건이었다. 이 실험은 한 가지 위치 변화 조건에서 수행했으며, 다른 외력이나 초기 배치 분포에서 재시도가 얼마나 자주 필요한지는 따로 측정해야 한다.

## 조건과 판정

Python MuJoCo의 `shifted` / `feedback` 조합이다. 같은 seed의 초기 물체 좌표를 짝별로 확인했다. 첫 관측 후 물체에 +Y 방향 2 N을 60 ms 가하고 350 ms 기다린다. 접근 후 후면 카메라로 재관측하고, 들어 올린 뒤 손가락 간격이 18 mm를 초과하면 집기로 판정한다. 재시도는 빈 집기 판정 뒤 손을 열고 다시 관측하는 동작을 포함한다.

배치 성공 조건은 최종 물체 중심이 트레이 중심 (0.48, 0.24) m에서 X/Y 각각 65/60 mm 미만, 높이 0.37 m 초과·0.42 m 미만, 최종 손가락 간격 65 mm 초과, 로봇–가림판 접촉 0건이다. 표의 거리는 종료 시점 물체 중심에서 트레이 중심까지의 XY 거리다. 벽시계 시간은 Codespaces 실행 로그의 값이며 호스트 부하에 영향을 받는다.

## 원본 확인과 재집계

[Codespaces 원본 압축 파일](records.tar.gz) · [실행별 CSV 42행](runs.csv) · [집계 코드](../../../scripts/summarize_retry_study.py)

압축 파일에 42개의 `run.json`과 그 안에서 참조한 관측 86개(JPG·NPZ 각 86개), 별도 seed 107 관측 NPZ 1개, 실험 당시 Python 파일 3개가 들어 있다. 결과 JSON에는 관측·집기 이벤트와 관절·모터 trace가 있다. 업로드 원본을 그대로 보관했다. 압축 파일의 테스트 스크립트는 크기 불일치 예외를 확인하던 당시 버전이다. 정리된 자동 테스트와 실행 방법은 [RGB-D 검사 문서](../RGBD_VALIDATION.md)에 있다.

저장소 루트에서 실행한다. 원본의 SHA-256, 42개의 설정·성공 판정·거리·관측 및 재시도 횟수, 21쌍의 초기 좌표, 보관 CSV와의 일치를 확인할 수 있다.

```bash
study=docs/v3/retry-study
echo "81370859959e5dd9932b45e52d5b73c6b847489f73b40d864c461f7adff81b1f  $study/records.tar.gz" | sha256sum -c -
mkdir -p work/retry-archive
tar -xzf "$study/records.tar.gz" -C work/retry-archive
python -m scripts.summarize_retry_study work/retry-archive/work/retry-study > work/retry-archive/runs.csv
diff "$study/runs.csv" work/retry-archive/runs.csv
```

## 시뮬레이션 재현

[환경 설치](../../../README.md#실행과-재현) 후 저장소 루트에서 실행한다. 원본 실험은 `ENABLE_RETRY`를 바꾸어 실행했다. 현재 CLI에서는 `--no-retry`로 같은 설정을 선택한다. 아래 명령은 Linux Bash 기준이다.

```bash
set -e
export MUJOCO_GL=egl
base=work/retry-reproduction
for mode in off on; do
  flags=()
  if [[ "$mode" == off ]]; then flags+=(--no-retry); fi
  for seed in 107 {200..219}; do
    out="$base/eval-$mode/seed$seed"
    if [[ "$seed" == 107 ]]; then out="$base/seed107-$mode"; fi
    python -m manipulation.controller --condition shifted --method feedback \
      --seed "$seed" "${flags[@]}" --out "$out" > /dev/null
  done
done
python -m scripts.summarize_retry_study "$base" > "$base/runs.csv"
```

원본의 86개 관측에서 RGB-D 위치 추정값을 다시 계산해 로그와 대조했다. 별도 Linux 환경(Python 3.11, MuJoCo 4.0.1, EGL)에서 seed 107의 두 설정을 독립 재실행해 집기·배치 판정과 시뮬레이션 시간을 재현했다. 최종 거리 값에는 부동소수점 끝자리 차이가 있었고, 처리 시간은 환경마다 달라진다. 기존 [160회 벤치마크](../EXPERIMENT.md)의 결과와 이 후속 실험은 별도로 집계한다.
