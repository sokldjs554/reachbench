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

## 기록 비교 화면

[공개 비교 화면](https://reachbench-vision-control.ykh13571.chatgpt.site/retry/)은 두 실행의 첫 집기 확인 시점에서 열린다. 끔 기록은 6.31초에서 끝나고 켬 기록은 17.56초까지 이어진다. 공통 시간 슬라이더 아래의 사건 버튼으로 집기와 배치 시점으로 이동할 수 있다.

외부 시점 장면은 원본 관절·물체 자세로 MuJoCo에서 재구성했다. 첫 집기 실패(6.31초)와 두 번째 집기(12.51초)는 같은 고정 확대 카메라에서 보며, 배치 완료(17.56초)는 트레이 전체가 보이는 구도다. 재시도 끔의 마지막 자세는 6.31초, 켬의 첫·두 번째 판정에 쓰인 자세는 각각 6.30초와 12.50초다. [장면별 자세 시각과 카메라 설정](../../../dist/retry/event-views.json)에 원본 기록의 해시를 남겼다. 확대 사진만 다시 만들려면 저장소 루트에서 `MUJOCO_GL=egl python -m scripts.render_retry_events`를 실행한다. 포즈 샘플의 실제 시각은 각 화면에 표시된다. 아래의 카메라 사진은 각 실행에서 저장한 원본 센서 JPEG다. 사진을 선택하면 직전 상태와 다음 기록 명령을 확인할 수 있다. [관측–행동 자료와 생성 명령](ALIGNMENT.md).

비교 화면의 자세 프레임을 다시 만들려면 저장소 루트에서 실행한다.

```bash
MUJOCO_GL=egl python -m scripts.render_retry_replay --out work/rebuilt-frames
```

**공개 화면 검증 (2026-11-19, Sites v5).** Chromium의 [데스크톱 1440 × 1000](desktop.png)과 [모바일 뷰포트 390 × 844](mobile.png)에서 홈 진입, 공동 재생·정지·초기화, 시간 탐색, 두 번째 집기·배치 이동, 먼저 끝난 실행의 시간 고정, 관측 선택, 7축 기록과 JSONL 86행 다운로드를 확인했다. 화면 비교용 프레임과 정렬 데이터를 포함한 배포 파일 30개가 저장소와 바이트 단위로 일치했다.

```bash
python tests/browser_retry.py https://reachbench-vision-control.ykh13571.chatgpt.site/
```

**공개 화면 검증 (2026-11-26, Sites v16).** [홈의 변경 전후 미리보기](grasp-views-before-after.png)는 같은 공개 주소를 배포 전후에 캡처한 이미지다. Chromium 데스크톱 1440 × 1000과 모바일 너비 390 × 844에서 세 장면이 로드되고, 비교 화면의 시점 버튼·슬라이더·재생·일시정지가 작동하며, 끔 기록이 6.31초에 고정되는 것을 확인했다. WebGL을 끈 두 너비 모두 3D 영역의 안내 링크로 첫 집기 실패 비교를 열 수 있었다.

WebGL을 켠 Chromium에서는 SwiftShader로 MuJoCo를 실행했다. 데스크톱에서 seed 100의 네 조건과 두 방법을 조합한 여덟 실행을 끝까지 검사했다. 모바일 너비에서도 가림 조건에서 두 방법의 결과를 확인했다. 물리 단계는 묶어서 진행했으며, 모바일 검증에는 데스크톱 Chromium의 뷰포트를 사용했다.

```bash
python tests/browser_studio.py --url https://reachbench-vision-control.ykh13571.chatgpt.site/ --out work/public-studio
```
