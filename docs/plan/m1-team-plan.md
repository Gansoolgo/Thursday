# M1 팀별 실행 순서 (11/28 ~ 12/03)

> **📌 3줄 요약**
> - 팀을 **하드웨어 팀(로봇 A + 카메라 B)** 과 **소프트웨어 팀(GenAI C + System D)** 으로 나눕니다.
> - 날짜별로 **누가 무엇을 어떤 순서로** 하는지 적었습니다. 위에서부터 차례로 하면 됩니다.
> - 가장 중요한 것: **11/28 로봇 연결(#3)** 과 **준비물 구매(#31)**. 둘 중 하나라도 늦으면 나머지가 다 밀립니다.
>
> 관련: [dependencies.md](dependencies.md) 의존 관계·대비책 · [workflow.md](../workflow.md) GO/NO-GO · [results-m1.md](results-m1.md) · [스프린트 보드](https://github.com/orgs/Gansoolgo/projects/1)
> 📖 낯선 말은 👉 [용어집](../glossary.md)

---

## 0. 누가 누구인가

| 팀 | 이름 | 역할 | 담당자 |
|---|---|---|---|
| 🔧 하드웨어 | **A** | Robotics (로봇팔) | praykoo-cloud |
| 🔧 하드웨어 | **B** | Vision (카메라) | (확정 필요) |
| 💻 소프트웨어 | **C** | GenAI (음성·언어 모델) | (확정 필요) |
| 💻 소프트웨어 | **D** | System (통합·일정) | GodOfSeok |

- 하드웨어 팀은 로봇과 카메라를 **같이** 써야 해서 묶었습니다.
- 소프트웨어 팀은 **로봇 없이 바로 시작**할 수 있어서 묶었습니다.

---

## 1. 🔧 하드웨어 팀

**목표: "카메라로 본 물건을 로봇이 실제로 집는다"까지 확인하기**

### 📅 11/28 — 각자 따로

**A (로봇): [#3](https://github.com/Gansoolgo/Thursday/issues/3)**

1. 로봇 노트북에 Python 3.12 가상환경을 만들고 `lerobot` 설치
2. 팔을 USB로 꽂고 장치 관리자에서 COM 포트 번호 확인
3. 팔로워(따라 움직이는 팔) 캘리브레이션
4. 리더 팔(사람이 손으로 움직이는 팔)을 움직이면 팔로워가 따라오는지 **1분 동안** 확인
5. 되면 팔 2대 모두 같은 방식으로 확인 ([#40](https://github.com/Gansoolgo/Thursday/issues/40))
6. 설치 명령을 `docs/plan/setup-robot.md`에 적기

> 👉 **저녁까지 안 되면 바로 Discord에 알리기.** 대안(모터 직접 제어 / WSL / 다른 PC)으로 넘어갑니다 ([dependencies.md](dependencies.md) R1).

**B (카메라): [#37](https://github.com/Gansoolgo/Thursday/issues/37)**

1. HP60C 2대를 노트북에 꽂고 Python으로 컬러·깊이 영상 읽기 (`spikes/hp60c/`에 해 둔 것부터 이어서)
2. 한 대만 켤 때 vs 두 대 켤 때 깊이 값 비교 (서로 간섭하는지)
3. 30 · 40 · 50cm 높이에서 작업대가 다 보이는지 확인

### 📅 11/29 ~ 11/30 — 따로

**A: [#4](https://github.com/Gansoolgo/Thursday/issues/4)**

1. 칸 A → 칸 B로 집어서 놓기를 IK로 시켜 보기
2. **20번 반복**해서 몇 번 성공했는지 세기

**B: [#7](https://github.com/Gansoolgo/Thursday/issues/7)**

1. 시연 물건 사진 찍기 (로봇을 안 쓸 때)
2. Intel Geti로 학습 → OpenVINO로 인식되는지 확인

### 📅 12/01 — 둘이 같이

**A + B: [#5](https://github.com/Gansoolgo/Thursday/issues/5) 좌표 보정** (주 담당 B, 보조 A)

1. 작업대에 ArUco 마커(카메라가 위치를 알아보는 인쇄 표식) 붙이기
2. 카메라 화면의 점 → 로봇 좌표(mm)로 바꾸는 계산 만들기
3. 로봇을 그 좌표로 보내서 얼마나 빗나가는지 측정

### 📅 12/02 — 여유가 있으면

- A: [#39](https://github.com/Gansoolgo/Thursday/issues/39) 손수건 모서리 집기
- B: [#38](https://github.com/Gansoolgo/Thursday/issues/38) 깊이 카메라로 손 위치 읽기

### 로봇 같이 쓰기

- 로봇은 **오전 A · 오후 B**처럼 시간을 나눕니다.
- 쓰기 전에 Discord에 `로봇 14:00~15:00 (#5)`처럼 남깁니다 ([CONTRIBUTING.md](../../CONTRIBUTING.md) 6장).

---

## 2. 💻 소프트웨어 팀

**목표: "말하면 JSON 계획이 나온다"를 확인하고, 4명이 같이 쓸 약속(인터페이스)을 정하기**

### 📅 11/28

**D (System)**

1. **[#31](https://github.com/Gansoolgo/Thursday/issues/31) 준비물 구매**: 거치대, 조명, 작업대 판, 시연 물건, ArUco 마커 → 없으면 하드웨어 팀이 멈춥니다.
   > ⚠️ #31 목록은 예전 기준(LED·저항 케이스)입니다. 지금 기준(블록·블록 트레이, D-12·D-14)으로 바꿔서 삽니다.
2. **[#2](https://github.com/Gansoolgo/Thursday/issues/2) 장비 사양**: 노트북 CPU·GPU·NPU·메모리, 마이크 종류 적기
3. A가 로봇 설치에서 막히면 옆에서 같이 보기

**C (GenAI): [#6](https://github.com/Gansoolgo/Thursday/issues/6)**

1. `spikes/llm_plan.py` 만들기
2. 한국어 명령 20개 쓰기 (정상 12 · 모호 4 · 거절 4)
3. 소형 언어 모델 3개(Qwen3-4B, Phi-4-mini, EXAONE)를 노트북에서 돌려 JSON 계획이 잘 나오는지 비교

### 📅 11/29 ~ 11/30

**C: [#29](https://github.com/Gansoolgo/Thursday/issues/29) 음성 인식**

1. Whisper로 한국어 명령 녹음 → 텍스트 변환
2. 팀원 2명 이상이 명령 20개 녹음, 정확도와 걸리는 시간 측정

**D: [#8](https://github.com/Gansoolgo/Thursday/issues/8) 인터페이스 준비**

1. [interfaces.md](../interfaces.md) 9장 "합의가 필요한 질문" 6개 읽기
2. 질문마다 **추천 답**을 미리 써 두기 → 12/02 회의에서는 정하기만 하면 되게

### 📅 12/01

**C + D: [#30](https://github.com/Gansoolgo/Thursday/issues/30) 동시 실행 측정**

- 음성 인식 + 물체 인식(B의 결과) + 언어 모델을 노트북 하나에서 **동시에** 돌려도 느려지지 않는지 확인

---

## 3. 두 팀이 만나는 지점

| 날짜 | 무엇을 | 누가 |
|---|---|---|
| **11/28 저녁** | #3 로봇 연결이 됐는지 확인. 안 되면 대안으로 전환 | 4명 |
| **12/01** | 보정 오차·인식 결과를 공유 → World State 형식에 반영 | B ↔ D |
| **12/02** | M1 결과 공유, GO/NO-GO 판정, **#8 인터페이스 확정** | 4명 회의 |
| **12/03** | D가 공통 코드(`app/core/types.py`)와 가짜 로봇(`MockRobotArm`) 병합 → 다음 주부터 4명 모두 로봇 없이 개발 가능 | D → 전체 |

---

## 4. 모두 공통

- 무언가 해 보면 **그 Issue에 댓글로 숫자 한 줄**. 예: "20번 중 15번 성공", "Windows에서 포트를 못 찾음"
- 끝나면 AI에게 "#번호 기록 써 줘" → 양식에 맞춘 초안을 확인 ([records.md](../records.md))
- 매일 Discord 한 줄: 어제 한 것 / 오늘 할 것 / 막힌 것
- **30분 이상 혼자 막히면** 바로 물어보기
