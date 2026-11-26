# Thursday — 작업실 AI 조수 로봇팔

**T**ask-aware **H**elper that **U**nderstands, **R**earranges & **S**ets up **D**esks **A**daptively for **Y**ou

> 작업하는 사람 옆에서 **준비 → 보조 → 정리**를 돕는 로봇팔.
> 인터넷 없이 Intel AI PC 한 대로 동작합니다.

최종 프로젝트 · 2026-11-26 ~ 12-18 (구현 마감 12-17) · 팀: 신재석, 구경윤, 박휘성, 김효신

---

## 처음 왔다면

| 나는… | 이 순서로 읽으세요 | 시간 |
|---|---|---|
| **처음 보는 사람** (강사님 등) | 이 README → [시스템 아키텍처](docs/architecture.md) 1장 그림 | 5분 |
| **팀원, 첫날** | 이 README → [협업 규칙](CONTRIBUTING.md) → [Git 실전 가이드](docs/git-guide.md) → [AI에게 일 맡기는 법](docs/ai-guide.md) | 30분 |
| **팀원, 코드 짜기 전** | [인터페이스 규격](docs/interfaces.md)에서 내 모듈 부분 → 맡은 Issue | 10분 |
| **AI 도구** | [AGENTS.md](AGENTS.md) (Claude Code는 자동으로 읽음) | — |

---

## 무엇을 만드나

영화 속 작업실 조수 로봇팔처럼, 사람이 작업하는 동안 옆에서 필요한 물건을 꺼내 주고, 말하면 건네주고, 끝나면 다음 작업에 맞게 정리합니다.

| 단계 | 사용자가 하는 말 | 로봇이 하는 일 |
|---|---|---|
| 🧰 작업 전 · 준비 | "LED 실습 할 거야" | 필요한 부품을 작업 구역에 꺼내 둠, 빠진 부품 알림 |
| 🤝 작업 중 · 보조 | "저항 줘" | 해당 물건을 집어 전달 위치에 놓음 |
| 🧹 작업 후 · 정리 | "정리해 줘" | 자주 쓰는 것·다음에 쓸 것을 가까운 칸에 배치 |

**범용성:** 작업 종류(전자회로 실습, 조립, 교육 수업 등)가 바뀌어도 **엔진 코드는 그대로**, 작업 설명서와 물건 목록(데이터)만 바꿉니다.

## 어떻게 동작하나

```mermaid
flowchart LR
    User([사용자]) -->|말·텍스트| Planner
    Cam[웹캠] --> Vision[인식<br/>Geti 모델 + OpenVINO]
    Vision --> WS[(World State<br/>물건·칸·로봇 상태)]
    Manual[작업 설명서<br/>Skill 목록] --> Planner
    WS --> Planner[GenAI Planner<br/>OpenVINO GenAI 로컬 LLM]
    Planner -->|JSON 계획| Gate[검증 계층<br/>Safety Gate]
    Opt[배치 최적화<br/>사용 기록 기반] --> Gate
    Gate --> Arm[SO-101 로봇팔<br/>IK pick/place]
    Arm --> Verify[결과 확인]
    Verify --> WS
```

**지켜야 할 원칙 4가지**

1. **LLM은 모터를 직접 움직이지 않는다** — JSON 계획만 내고, Safety Gate가 통과시킨 Skill만 실행
2. **계산은 수학으로, 해석은 AI로** — 좌표·배치는 알고리즘, 말·설명서 해석은 GenAI
3. **완전 오프라인** — 인식·LLM·제어 모두 노트북 한 대
4. **숫자로 증명** — 성공률, 꺼내는 시간·이동 거리, 규칙 기반과 비교

## 기술 스택

| 영역 | 기술 |
|---|---|
| 물체 인식 | Intel Geti (학습) · OpenVINO Runtime (추론) · NNCF (양자화) |
| 계획·대화 | OpenVINO GenAI 로컬 LLM · JSON schema 제약 출력 |
| 로봇 제어 | SO-101 + LeRobot · 역기구학(IK) pick/place · (선택) ACT 모방학습 |
| 하드웨어 | Intel Core Ultra 5 225H (CPU·iGPU·NPU) · SO-101 · 웹캠 |
| 환경 | Windows 11 · Python 3.12 |

---

## 문서 지도

**📘 무엇을 왜 만드나 (기획)**

| 문서 | 한 줄 |
|---|---|
| [vision.md](docs/vision.md) | 문제, 가설, 성공 기준, 하지 않을 것 |
| [usecases.md](docs/usecases.md) | 사용자가 하는 일 그림, 시나리오 5개, 유저 스토리 12개 |

**📐 어떻게 만드나 (설계)**

| 문서 | 한 줄 |
|---|---|
| [architecture.md](docs/architecture.md) | 전체 구조·장치 배치·UML(클래스·시퀀스·상태) |
| [interfaces.md](docs/interfaces.md) | 모듈끼리 주고받는 데이터 형식 — **코드 짜기 전 필독** (초안, 12/02 확정) |

**🤝 어떻게 같이 일하나 (협업)**

| 문서 | 한 줄 |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | 팀 규칙: Issue → 브랜치 → PR → 리뷰 → 병합 |
| [git-guide.md](docs/git-guide.md) | Git·GitHub 실전: 처음 세팅, 하루 흐름, 실수 복구 |
| [ai-guide.md](docs/ai-guide.md) | AI에게 일을 정확히 맡겨 수정을 줄이는 법, 복사용 프롬프트 |
| [workflow.md](docs/workflow.md) | 일정, 애자일(스프린트·DoD·회고), GO/NO-GO |
| [AGENTS.md](AGENTS.md) | AI 도구가 지킬 공통 규칙 |

## 일정

| Milestone | 기간 | 목표 |
|---|---|---|
| M1 기술 검증 | 11/26 ~ 12/02 | 각 기술이 실제로 되는지 GO/NO-GO |
| M2 핵심 모듈 | 12/03 ~ 12/09 | 인식 · pick/place · LLM 계획 각각 동작 |
| M3 통합 | 12/10 ~ 12/14 | 말 한마디 → 결과 확인까지 종단 동작 |
| M4 완성·측정 | 12/15 ~ 12/17 | 교육 시나리오, 반복 시험, **구현 마감** |
| M5 발표 | 12/18 | 라이브 데모 |

진행 상황: [스프린트 보드](https://github.com/orgs/Gansoolgo/projects/1) · [Milestones](https://github.com/Gansoolgo/Thursday/milestones) · [Issues](https://github.com/Gansoolgo/Thursday/issues)

## 팀

| 역할 | 주요 담당 | 담당자 |
|---|---|---|
| System Architect | 요구사항, 인터페이스 규격, 통합, 일정 | 추후 결정 ([#1](https://github.com/Gansoolgo/Thursday/issues/1)) |
| Vision Engineer | Geti 학습, 추론, 좌표 보정, 결과 확인 | 추후 결정 |
| GenAI Engineer | 로컬 LLM, JSON 계획, Safety Gate | 추후 결정 |
| Robotics Engineer | SO-101, IK pick/place, 안전 정지, 최적 배치 | 추후 결정 |

## 현재 상태

🟡 **출발 준비 단계.** 코드와 하드웨어 검증 결과는 아직 없습니다. 설계는 M1 결과에 따라 바뀔 수 있습니다.

## AI 도구 사용 공개

기획 정리와 문서 작성에 ChatGPT와 Claude(Claude Code)를 사용했습니다. 사용 내역은 커밋의 `Co-Authored-By`와 PR 본문에 남깁니다.
