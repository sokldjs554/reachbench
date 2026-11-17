from pathlib import Path
import json,markdown,html,platform,subprocess
s=json.loads(Path('dist/data/summary.json').read_text())
m=s['metrics'];lines=['## 실제 실행 결과','',f"환경: CPython {platform.python_version()}, Linux x86_64, NumPy 2.2.6, OpenCV 4.11.0.86, PyBullet 3.2.7, CPU DIRECT/TinyRenderer. GPU 미사용. 평가 400회 벽시계 시간 {s['wall_seconds']:.1f}초. 실행일 2026-11-17 KST.",'','| 방법 | 성공 / 전체 | 성공률 | 검출 수 | 인식 오차 평균 | 인식 중앙값 | 계획 중앙값 |','|---|---:|---:|---:|---:|---:|---:|']
names={'baseline':'RGB + 직접 접근','perception':'HSV + 직접 접근','planning':'RGB + A*','improved':'HSV + A*'}
for k in names:
 r=m[k]['all'];lines.append(f"| {names[k]} | {r['successes']}/{r['n']} | {r['success_rate']:.0%} | {r['detected_n']} | {r['perception_error_mean_mm']:.2f} mm | {r['perception_median_ms']:.2f} ms | {r['planning_median_ms']:.2f} ms |")
lines+=['','| 조건 | 기준 성공 | 개선 성공 | 개선 인식 오차 |','|---|---:|---:|---:|']
conds={'nominal':'기본 조명','dim':'어두운 조명','clutter':'추가 장애물','occluded':'목표 가림','calibration':'보정 오차 +65 mm'}
for c,name in conds.items():
 a,b=m['baseline'][c],m['improved'][c];err='검출 없음' if b['perception_error_mean_mm'] is None else f"{b['perception_error_mean_mm']:.2f} mm";lines.append(f"| {name} | {a['successes']}/20 | {b['successes']}/20 | {err} |")
lines+=['','기준 2% → 개선 59%는 이 조건 혼합의 관측값이다. 주된 개선은 경로 계획에 있다(RGB+A*:39%). HSV 인식만 바꾼 경우는 3%에 그쳤고, A*와 결합했을 때 어두운 조명에서 추가 20건을 성공했다. 모든 실패를 포함한 집계다. 59%를 일반 로봇 성공률이나 회사 벤치마크와 비교하지 않는다.','','개선 방법의 실패는 목표 미검출 20건, 목표 자세 차단 1건, 충돌 17건, 최종 위치 오차 초과 3건이었다. 충돌 17건과 위치 오차 3건은 모두 보정 오차 조건에서 발생했다.','',f"전체 개선 성공률 Wilson 95% 구간: {m['improved']['all']['wilson95'][0]:.1%}–{m['improved']['all']['wilson95'][1]:.1%}. 계획 P95 {m['improved']['all']['planning_p95_ms']:.2f} ms. 기본 조명 계획 P95 {m['improved']['nominal']['planning_p95_ms']:.2f} ms로, 평균적인 실시간 동작을 보장하지 않는다.",'','### 기록으로 추적하는 사례','']
for reason in ['reached','goal_blocked','target_missing','collision','position_error']:
 row=next(r for r in s['episodes'] if r['method']=='improved' and r['reason']==reason)
 lines.append(f"- `{row['id']}`: {reason}, 최종 오차 {row['endpoint_error_mm']:.2f} mm. `dist/data/{row['id']}.json`에서 입력·추정·관절·판정을 확인한다.")
lines+=['','### 검증 결과','','- Python 테스트 11개: FK/IK, 카메라 왕복, 픽셀 검출, 경로 중간 충돌, Bullet 기하 일치, 집계 수식, 재현성, 전수 기록, 새 계산 HTTP API 및 잘못된 입력 거부.','- 400개 실행 기록·100개 RGB 입력 무결성 및 집계 재계산 통과. 제외 기록 0개.','- DOM 검사: 다섯 조건·seed·두 방법 수치·시간 슬라이더·재생/초기화·탭·오버레이·다운로드 연결 통과.','- 실제 브라우저 렌더링, 화면 크기별 육안 확인, 키보드/스크린리더 수동 검증, 외부 사용자 사용성 테스트는 미실시. 관리 환경의 지원 브라우저 제어 도구 `cua_repl.js`가 없어서 브라우저 QA를 수행할 수 없었다. DOM 테스트를 브라우저 테스트로 간주하지 않는다.','','### 배포·소스 범위','','정적 배포판은 실제로 생성한 이미지와 궤적을 선택·비교·재생한다. 실시간 PyBullet 계산이나 임의 좌표 실행은 로컬 Python 서버에서 수행한다. Sites 배포는 소유자 전용이다. 소스와 실험 기록은 공개 GitHub 저장소 https://github.com/sokldjs554/reachbench 에서 제공한다. 외부 면접관에게 링크를 전달하기 전에 접근 설정을 확인하거나 ZIP의 dist 디렉터리를 별도 정적 호스팅에 배포한다.']
results='\n'.join(lines)+'\n';Path('docs/RESULTS.md').write_text(results)
parts=[('# ReachBench · 프로젝트 보고서\n\n[데모로 돌아가기](./index.html) · [소스와 실험 기록 ZIP](./reachbench-source.zip)\n\n카메라 인식 결과가 로봇팔 동작의 성공과 실패에 어떻게 연결되는지 확인하는 CPU 시뮬레이션입니다.\n\n**모든 조사·설계·구현·평가 작업은 Codex가 수행했습니다. 지원자가 직접 수행했다고 확인된 개발·실물 실험은 없습니다.**\n\n'),Path('docs/RESEARCH.md').read_text(),Path('docs/EXPERIMENT.md').read_text(),results,Path('docs/INTERVIEW.md').read_text(),Path('docs/THIRD_PARTY.md').read_text()]
content=markdown.markdown('\n\n---\n\n'.join(parts),extensions=['tables','fenced_code'])
Path('dist/report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReachBench 실험 보고서</title><link rel="stylesheet" href="style.css"></head><body><article class="report">'+content+'</article></body></html>')
