# 외부 자산과 사용 범위

- [MuJoCo](https://github.com/google-deepmind/mujoco): Python 및 공식 npm `@mujoco/mujoco` **4.0.1**, Apache-2.0. 물리 계산·오프스크린 센서·WASM 실행. [동봉 라이선스](../../dist/vendor/MUJOCO-LICENSE.txt).
- [MuJoCo Menagerie / Franka Emika Panda](https://github.com/google-deepmind/mujoco_menagerie/tree/370c43965323c0944b433b202aac5058b5f907a9/franka_emika_panda): commit `370c43965323c0944b433b202aac5058b5f907a9`, Apache-2.0. 모델 XML·메시를 보존하고 별도 `workcell.xml`에서 베이스 위치, 테이블·물체·트레이·센서와 작업 파라미터를 추가했다. [라이선스](../../manipulation/assets/panda/LICENSE), [각 파일 SHA-256](../../manipulation/assets/panda/provenance.json). 브라우저에서는 같은 모델의 컴파일된 MJB를 gzip으로 제공한다.
- [Three.js](https://github.com/mrdoob/three.js): **0.180.0**, MIT. 브라우저 시각화·RGB와 depth 센서 렌더링·OrbitControls. [라이선스](../../dist/vendor/THREE-LICENSE.txt).
- NumPy 2.2.6(BSD-3-Clause), OpenCV 4.11.0.86(Apache-2.0): CPU 배열 계산·영상 분할·저장.
- 공개 데이터셋과 사전학습 가중치는 사용하지 않았다. `dist/bench`의 센서·action·평가 자료는 이 작업에서 실제로 생성한 합성 데이터다. 모델과 라이브러리의 라이선스는 이 자료의 실기 타당성이나 안전성을 보증하지 않는다.

18개 사례의 README·데모는 비교 조사에만 활용했다. 타 프로젝트의 코드·UI·영상·브랜드를 데모 자산으로 복제하지 않았다. 조사에서 본 동작과 직접 재현한 성과는 [RESEARCH.md](RESEARCH.md)에 구분했다.
