"""Build the current report from actual evaluation summaries; preserve v1 records."""
from pathlib import Path
import json,re,posixpath
import markdown
root=Path(__file__).resolve().parents[1]
s=json.loads((root/'dist/data-v2/summary.json').read_text())
lines=['# 기준점 보정: 실제 평가 결과','','2026-11-17 KST · CPU 기구학 시뮬레이션. 개발 42회와 분리한 최종 280회. 정상 기준점의 100개 paired 장면과 스트레스 40개 paired 장면을 구분한다. 기존 400회 평가와 seed·조건이 다르므로 기존 59%와 새 100%를 직접 개선 폭으로 비교하지 않는다.','','## 정상 기준점: 편향별 동일 20개 장면','','| X 편향 | 성공 기존→보정 | 충돌 기존→보정 | 목표 인식 평균 오차 mm | 최종 거리 평균 mm | 처리 중앙값 ms |','|---|---:|---:|---:|---:|---:|']
for bias in s['config']['offsets_mm']:
    m=s['metrics']['standard'][str(bias)];a,b=m['uncorrected'],m['reference']
    lines.append(f"| +{bias} mm | {a['successes']}/20 → {b['successes']}/20 | {a['collisions']} → {b['collisions']} | {a['perception_error_mean_mm']:.2f} → {b['perception_error_mean_mm']:.2f} | {a['endpoint_error_mean_mm']:.2f} → {b['endpoint_error_mean_mm']:.2f} | {a['pipeline_median_ms']:.2f} → {b['pipeline_median_ms']:.2f} |")
a,b=s['metrics']['standard']['all'].values()
lines += ['',f"정상 기준점 전체 성공 **{a['successes']}/100 → {b['successes']}/100**, 충돌 {a['collisions']} → {b['collisions']}. 평균 인식 오차 {a['perception_error_mean_mm']:.2f} → {b['perception_error_mean_mm']:.2f} mm. 처리 중앙값 {a['pipeline_median_ms']:.2f} → {b['pipeline_median_ms']:.2f} ms, P95 {a['pipeline_p95_ms']:.2f} → {b['pipeline_p95_ms']:.2f} ms. 기준점 처리 자체 중앙값 {b['calibration_median_ms']:.2f} ms.",'',f"성공률 Wilson 95%: 기존 {a['wilson95'][0]:.1%}–{a['wilson95'][1]:.1%}, 보정 {b['wilson95'][0]:.1%}–{b['wilson95'][1]:.1%}. 편향 간 같은 seed를 재사용한 상관을 보정하지 않은 근사 구간이다. 높은 P95와 공유 CPU의 부하를 감안할 때 실시간 제어 성능을 주장할 수 없다.",'','## 기준점 가정이 깨질 때','','| 조건 | 성공 기존→보정 | 충돌 기존→보정 | 보정 후 인식 오차 | 보정 후 최종 거리 | 보정 후 실패 전수 |','|---|---:|---:|---:|---:|---|']
for p,name in [('markers_missing','기준점 2개'),('board_shift','기준점 전체 +50 mm 오배치')]:
    a,b=s['metrics'][p]['all'].values();reasons=', '.join(f'{k} {v}회' for k,v in b['reasons'].items())
    lines.append(f"| {name} | {a['successes']}/20 → {b['successes']}/20 | {a['collisions']} → {b['collisions']} | {b['perception_error_mean_mm']:.2f} mm | {b['endpoint_error_mean_mm']:.2f} mm | {reasons} |")
lines+=['','기준점 부족에서는 전부 이동을 보류해 충돌을 피했지만 과제는 실패했다. 표시되는 최종 거리는 움직이지 않은 시작 손끝에서 목표까지다. 목표 추정은 남아 있어도 계획기에 전달하지 않는다. 기준점 오배치에서는 내부 잔차가 작아도 절대 좌표가 틀리므로 성공하지 못했다. 잔차 검증만으로 공동 배치 오류를 검출할 수 없다는 반례다.','','정상/스트레스를 모두 합치면 두 방법 성공은 40/140과 100/140이다. UI 상단 40%→100%는 **정상 기준점 100개 장면만의 비율**이며 스트레스를 제외했다는 사실을 표시한다. 성공한 사례를 선별한 것이 아니라 사전에 정의한 조건별 분모를 사용했다.','','## 추적 가능한 성공·실패 사례','']
for p,reason in [('standard','reached'),('standard','collision'),('standard','position_error'),('markers_missing','calibration_unavailable'),('board_shift','position_error'),('board_shift','no_path')]:
    r=next(r for r in s['episodes'] if r['profile']==p and r['reason']==reason)
    lines.append(f"- [{r['id']}](../../dist/data-v2/{r['id']}.json): {reason}, 목표 인식 {r['perception_error_mm']:.2f} mm, 최종 거리 {r['endpoint_error_mm']:.2f} mm.")
lines+=['','## 검증과 공개 범위','','- Python 테스트 21개 통과: 원 엔진/기하/API 11개와 보정·기준점 실패·held-out 재실행·집계·영상 정합성 검증.','- 최종 280회 **전수 재실행**: RGB 해시·검출·보정값·관절 trace·판정·최종/인식 오차 완전 일치. 타이밍은 비교하지 않음. [검증 기록](reproduction.json).','- 기존 기준/개선 200회 재실행이 원본과 일치. 총 480개 실행의 프레임 trace SHA-256·t·q, 페이지 이미지 해시/크기, 접촉 샘플 검사 통과. 기존 400회 원본 데이터 보존.','- Chromium 1440×1000 및 모바일 390×844: 재생·정지·초기화·시간 탐색, 프레임/2D 동일 index, 가림·보정·기준점 결손·오배치, 실패 링크, seed 변경, 결과 표, 탭, 오버레이 검사 통과. [브라우저 검사](browser-validation.json), [DOM 검사](dom-validation.json).','- 실제 캡처: [데스크톱](../../dist/screenshots/desktop-comparison.png), [모바일](../../dist/screenshots/mobile-comparison.png), [보정 비교](../../dist/screenshots/desktop-calibration.png).','- 외부 면접관/사용자 대상 사용성 테스트, 실제 iOS Safari/Android 기기, 전체 키보드·스크린리더 감사는 미실시. 모바일은 Chromium viewport/touch 에뮬레이션이다.','- 관리 preview relay는 준비 시간 초과로 실패했다. 로컬 정적 파일을 Chromium 요청에 연결해 실제 JS·레이아웃을 검사했고 공개 배포에는 별도 실제 HTTP 검증을 사용한다. DOM 검사와 브라우저 검사를 구분한다.','','공개 데모는 사전 계산된 기록 재생이며 Python을 브라우저 서버에서 실행하지 않는다. 로컬 Python 서버에서 새 목표 좌표를 계산할 수 있다. 새 보정 실험을 임의 조건으로 실행하려면 CLI를 사용한다. 모든 결과는 시뮬레이션이며 실물 로봇·학습 정책·파지·ROS 2 성능이 아니다.']
(root/'docs/v2/RESULTS.md').write_text('\n'.join(lines)+'\n')
intro='# ReachBench · 실행과 실패를 확인하는 실험 보고서\n\n[공개 데모](./index.html) · [GitHub](https://github.com/sokldjs554/reachbench) · [소스·데이터 ZIP](https://github.com/sokldjs554/reachbench/archive/refs/heads/main.zip)\n\n카메라 인식 → 위치 추정 → 경로 계획 → 목표 접근 → 평가를 연결합니다. **초기 구현·실험 실행·검증·문서화에 Codex를 사용했습니다.**\n\n![실제 Chromium 데스크톱 화면](screenshots/desktop-comparison.png)\n\n'
parts=[intro]
for name in ['docs/v2/RESULTS.md','docs/v2/RESEARCH.md','docs/v2/EXPERIMENT.md','docs/THIRD_PARTY.md','docs/RESEARCH.md','docs/RESULTS.md']:
    content=(root/name).read_text()
    def link(m):
        target=m.group(2)
        if re.match(r'https?://|#',target):return m.group(0)
        absolute=posixpath.normpath(posixpath.join(posixpath.dirname(name),target))
        url='https://github.com/sokldjs554/reachbench/blob/main/'+absolute
        if absolute.startswith('dist/'):url=absolute[5:]
        return f'[{m.group(1)}]({url})'
    parts.append(re.sub(r'\[([^\]]*)\]\(([^)]+)\)',link,content))
content=markdown.markdown('\n\n---\n\n'.join(parts),extensions=['tables','fenced_code'])
(root/'dist/report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReachBench 실험 보고서</title><link rel="stylesheet" href="style.css"></head><body><article class="report">'+content+'</article></body></html>')
print('Report generated from actual summaries; v1 results unchanged.')
