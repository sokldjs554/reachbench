# 출처와 라이선스

외부 데이터셋·사전학습 가중치·CAD/URDF·텍스처·사진·폰트 파일을 내려받아 사용하지 않았다. 모든 실험 장면은 코드의 기본 도형으로 생성했다. RGB 이미지·정답 좌표·궤적은 이 시뮬레이션의 합성 데이터다. 생성 코드·문서·생성 데이터는 이 저장소의 MIT 라이선스로 제공한다. 회사와 도구의 명칭·상표 권리는 각 소유자에게 있다.

| 의존성 | 고정 버전 | 라이선스 / 원문 | 사용 범위 |
|---|---|---|---|
| CPython | 실행 3.11.18 | [PSF](https://docs.python.org/3/license.html) | 실행 환경 |
| PyBullet | 3.2.7 | [zlib; 일부 번들 예제/서드파티 예외](https://github.com/bulletphysics/bullet3/blob/master/LICENSE.txt) | DIRECT, TinyRenderer, 도형·관절·충돌 쿼리. pybullet_data 자산 미사용 |
| OpenCV | 4.11.0.86 wheel | [Apache-2.0](https://github.com/opencv/opencv/blob/4.11.0/LICENSE); wheel의 서드파티 고지 별도 | HSV, morphology, contours, PNG 입출력 |
| NumPy | 2.2.6 | [BSD-3-Clause](https://github.com/numpy/numpy/blob/v2.2.6/LICENSE.txt) | 수치 연산·난수 |
| pytest | 8.3.5 | [MIT](https://github.com/pytest-dev/pytest/blob/8.3.5/LICENSE) | Python 검증 |
| jsdom | 26.0.0 | [MIT](https://github.com/jsdom/jsdom/blob/26.0.0/LICENSE.txt) | 개발 시 DOM 동작 검사; 데모 런타임 미포함 |

라이브러리 바이너리·node_modules는 배포 소스 ZIP에 넣지 않았다. 설치 시 각 패키지의 라이선스와 배포 조건이 적용된다. 웹 런타임은 표준 HTML/CSS/JS이며 CDN·외부 글꼴·분석 추적기를 사용하지 않는다.

공고·회사·디자인 참고 페이지는 docs/RESEARCH.md에 링크하고 필요한 사실만 요약했다. 원문 페이지와 제품 이미지를 재배포하지 않았다.

## v2 추가 사용 범위

- OpenCV의 WebP 인코더로 실제 TinyRenderer 프레임을 타일링했다. 브라우저 이미지는 생성형 모델의 영상이 아니다.
- [Playwright 1.62.0 / Apache-2.0](https://github.com/microsoft/playwright/blob/main/LICENSE): 개발용 실제 Chromium 브라우저 검사. 공개 런타임·소스 ZIP에 바이너리를 넣지 않는다.
- [Chromium / BSD 계열 및 서드파티 고지](https://chromium.googlesource.com/chromium/src/+/main/LICENSE): 현재 환경에 설치된 headless 브라우저로 실제 화면 캡처.
- [Python-Markdown 3.7 / BSD](https://github.com/Python-Markdown/markdown/blob/3.7/LICENSE.md): 문서의 정적 HTML 생성, 런타임 의존성 아님.
- 사용자가 지정한 로봇팔·관측 프로젝트와 RoboEval/Foxglove는 [보완 조사](v2/RESEARCH.md)에 원문과 사용 범위를 기록했다. 코드·이미지·모델·영상 자산을 복제하지 않았다.
