# 공개 배포 검증

2026-11-17 KST. Sites v2 배포 상태 succeeded, audience public. 로그인 없는 HTTP 요청 및 실제 Chromium에서 확인했다.

- 공개 주소: https://reachbench-vision-control.ykh13571.chatgpt.site/
- 실행 코드·데이터 GitHub 커밋: `d5496db321db404b6e90ab266081883a1fa6cfcf`
- 대응 Sites 소스 커밋: `6ec546893358b0beb859cbd9fd71d760f7f22293`
- 배포 ID: `appgdep_6afbc2e149388191a4d2f128e80eb558`
- GitHub와 Sites의 전체 추적 파일 2,234개가 바이트 단위로 동일함을 확인했다. GitHub 원격의 README, 보정 코드, 새 집계도 해당 커밋과 대조했다.
- 공개 HTTP에서 HTML/JS/CSS/보고서/원본·신규 집계/설정/기록 메타데이터/실제 WebP/모바일 캡처 총 11개 파일의 SHA-256이 로컬 최종 파일과 일치했다. 모든 공개 자산을 개별 다운로드한 검사는 아니다. [HTTP 근거](public-http-validation.json).
- 실제 공개 URL에서 Chromium 데스크톱 1440×1000, 모바일 viewport 390×844의 주요 흐름을 모두 다시 실행했다. [브라우저 근거](public-browser-validation.json).
- 인증 쿠키 없이 접근했다. HTTP 파일 검사는 시스템 TLS 검증을 사용했다. 브라우저 검사는 환경 프록시 인증서 때문에 테스트 context에서 인증서 검증을 끈 것이므로 TLS 감사로 해석하지 않는다.

이 문서와 두 public-*-validation.json은 배포 후 얻은 증거를 추가하는 문서 전용 후속 커밋이다. 배포된 dist/코드/실험 데이터에는 후속 변경이 없다. 실제 휴대전화·Safari·스크린리더·외부 사용자 테스트는 수행하지 않았다.
