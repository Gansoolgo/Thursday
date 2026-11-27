# app/ui/assets

| 파일 | 내용 | 출처 |
|---|---|---|
| `so101_lowpoly.json` (약 350 KB) | SO-101 팔 3D 보기용으로 줄인 메시 (꼭짓점 mm · 삼각형 번호) | SO-101 URDF 의 STL 메시를 2.5 mm 격자로 합쳐 줄임. 원본: SO-ARM100 (TheRobotStudio), onshape-to-robot 으로 만든 so101.urdf — 라이선스 (확인 필요, 원본 레포는 Apache-2.0 로 알고 있음) |

- 화면의 3D 팔(아래 "보기" → 3D · 관절값)만 씁니다. 로봇 제어에는 쓰지 않습니다.
- 다시 만들 때: STL 폴더를 격자 크기 0.0025 m 로 줄이는 스크립트(시안 작업 때 사용)를 `scripts/` 에 따로 올릴 예정 (확인 필요).
