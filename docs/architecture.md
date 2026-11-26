# 시스템 아키텍처 (High Level Design)

> **📌 3줄 요약**
> - 흐름: **말 → LLM 계획(JSON) → Safety Gate → 로봇 실행 → 카메라로 확인 → 실패하면 재계획.**
> - AI가 판단하는 부분(Planner, 인식)과 결정론적으로 계산·검사하는 부분(좌표, 최적화, Gate, 실행)을 분리.
> - 모든 계산은 노트북 한 대: LLM은 iGPU, 인식은 NPU, 제어는 CPU (M1에서 실측 후 확정).
> 📖 낯선 말은 👉 [용어집](glossary.md)

> 상태: 초안 v0.2 (2026-11-26). M1 기술 검증 결과에 따라 바뀔 수 있습니다. 아직 구현된 코드는 없습니다.

## 목차
1. [전체 구조](#1-전체-구조)
2. [장치 배치 (Deployment)](#2-장치-배치-deployment)
3. [모듈별 역할](#3-모듈별-역할)
4. [클래스 다이어그램: 공통 데이터와 Skill](#4-클래스-다이어그램-공통-데이터와-skill)
5. [시퀀스 다이어그램](#5-시퀀스-다이어그램)
6. [상태 다이어그램: 실행 FSM](#6-상태-다이어그램-실행-fsm)
7. [범용성을 만드는 구조](#7-범용성을-만드는-구조)
8. [안전 설계](#8-안전-설계)
9. [폴더 구조](#9-폴더-구조)

---

## 1. 전체 구조

입력 → 이해 → 계획 → 검증 → 실행 → 확인의 닫힌 루프입니다. **AI가 판단하는 부분(주황)** 과 **결정론적으로 계산·검사하는 부분(파랑)** 을 분리했습니다.

```mermaid
flowchart TD
    subgraph Input[입력]
        U[사용자 명령<br/>텍스트 · 선택: 음성]
        C[웹캠 영상]
    end

    subgraph Perception[인식]
        V[물체 인식<br/>Geti 모델 + OpenVINO]
        K[좌표 변환<br/>픽셀 → 작업대 mm]
    end

    subgraph Knowledge[지식]
        M[작업 설명서<br/>tasks/*.yaml]
        R[Skill Registry<br/>실행 가능한 동작 목록]
        H[(사용 기록<br/>usage log)]
    end

    WS[(World State<br/>물건 · 칸 · 로봇 · 안전 상태)]

    subgraph Brain[계획]
        P[GenAI Planner<br/>로컬 LLM · JSON 출력]
        O[배치 최적화<br/>칸 배정 알고리즘]
    end

    G{검증 계층<br/>Safety Gate}

    subgraph Act[실행]
        A[Action Manager]
        IK[IK pick/place<br/>LeRobot kinematics]
        ARM[SO-101 로봇팔]
    end

    F[결과 확인<br/>행동 전후 비교]

    U --> P
    C --> V --> K --> WS
    M --> P
    R --> P
    WS --> P
    H --> O
    WS --> O
    P -->|계획 JSON| G
    O -->|칸 배정| G
    G -->|통과| A --> IK --> ARM
    G -->|거절·질문| U
    ARM --> F
    C --> F
    F --> WS
    F -->|기록| H
    F -->|실패| P

    classDef ai fill:#ffe5cc,stroke:#e67e22
    classDef det fill:#dbeafe,stroke:#2563eb
    class P,V ai
    class K,O,G,A,IK,F det
```

## 2. 장치 배치 (Deployment)

모든 계산은 **Intel 노트북 한 대**에서 합니다. 인터넷은 쓰지 않습니다. 장치 배정은 계획이며 M1에서 실측해 확정합니다.

```mermaid
flowchart LR
    subgraph PC[Intel Core Ultra 5 225H 노트북]
        subgraph CPU[CPU]
            APP[메인 앱 · Action Manager<br/>배치 최적화 · IK 계산]
        end
        subgraph GPU[iGPU]
            LLM[로컬 LLM<br/>OpenVINO GenAI INT4]
        end
        subgraph NPU[NPU]
            DET[물체 인식 모델<br/>OpenVINO INT8]
        end
        UI[대시보드<br/>Streamlit]
    end
    CAM[웹캠] -->|USB| PC
    PC -->|USB 직렬| ARM[SO-101 팔로워]
    ESTOP[비상 정지 버튼] --> PC
```

| 장치 | 맡는 일 | 이유 |
|---|---|---|
| iGPU | 로컬 LLM | 생성 모델은 메모리·연산량이 커서 iGPU가 적합 |
| NPU | 물체 인식 | 정적 입력 크기의 작은 모델을 저전력으로 상시 실행 |
| CPU | 제어 루프, IK, 최적화, 검증 | 결정론적·저지연 처리 |

## 3. 모듈별 역할

| 모듈 | 하는 일 | 하지 않는 일 |
|---|---|---|
| Vision | 물건 종류·위치 인식, 픽셀 → 작업대 좌표 변환, 칸 점유 판단 | 학습하지 않은 물건의 신뢰성 보장 |
| GenAI Planner | 자연어 목표·작업 설명서 해석, Skill 조합 계획(JSON), 모호하면 질문 생성 | 모터 명령 생성, 안전 규칙 변경 |
| Layout Optimizer | 사용 기록으로 물건별 칸 배정 (가까운 칸 = 자주·곧 쓸 물건) | 자연어 해석 |
| Safety Gate | 스키마·대상 존재·좌표 범위·금지 동작·재시도 횟수 검사 | 계획 수정 (거절·질문만) |
| Action Manager | Skill 순서 실행, 단계마다 상태 재확인, 시간 제한·실패 처리 | 계획 생성 |
| Robot (IK) | 목표 좌표로 집기·놓기, 속도·작업 영역 제한 | 판단 |
| Verifier | 행동 전후 영상 비교로 성공 판정, 사용 기록 저장 | |

## 4. 클래스 다이어그램: 공통 데이터와 Skill

모듈 사이에 주고받는 데이터 형식입니다. 이 형식을 먼저 합의해야 팀원이 동시에 개발할 수 있습니다. 필드·JSON 스키마·실패 코드 상세는 [interfaces.md](interfaces.md)에 있습니다.

```mermaid
classDiagram
    class WorldState {
        +str scene_id
        +datetime timestamp
        +List~ObjectInfo~ objects
        +Dict~str, Slot~ slots
        +RobotState robot
        +SafetyState safety
        +find(name) List~ObjectInfo~
    }
    class ObjectInfo {
        +str id
        +str cls
        +float confidence
        +Tuple pose_mm
        +str slot_id
    }
    class Slot {
        +str id
        +str zone
        +Tuple center_mm
        +str occupied_by
    }
    class RobotState {
        +str state
        +bool calibrated
    }
    class SafetyState {
        +bool estop
        +bool human_in_zone
    }
    class TaskManual {
        +str task_id
        +str name
        +List~str~ required_objects
        +List~str~ steps
    }
    class Plan {
        +str goal
        +List~PlanStep~ steps
        +str question
    }
    class PlanStep {
        +str skill
        +Dict args
    }
    class Skill {
        <<interface>>
        +str name
        +Dict input_schema
        +check_precondition(WorldState) bool
        +execute(args) SkillResult
    }
    class SkillResult {
        +str status
        +str failure_code
        +Dict observations
    }
    class SafetyGate {
        +validate(Plan, WorldState) GateDecision
    }
    class Planner {
        +plan(goal, WorldState, List~TaskManual~) Plan
    }
    class LayoutOptimizer {
        +assign(objects, slots, usage_log) Dict
    }

    WorldState "1" *-- "many" ObjectInfo
    WorldState "1" *-- "many" Slot
    WorldState *-- RobotState
    WorldState *-- SafetyState
    Plan "1" *-- "many" PlanStep
    Planner ..> Plan : 생성
    Planner ..> TaskManual : 참조
    SafetyGate ..> Plan : 검사
    Skill ..> SkillResult : 반환
    Skill <|.. PickPlace
    Skill <|.. HandOver
    Skill <|.. VerifyResult
    Skill <|.. AskUser
```

### 등록할 Skill (초안)

| Skill | 인자 | 실행 조건 | 성공 판정 |
|---|---|---|---|
| `detect_objects` | 없음 | 카메라 정상 | 인식 목록 갱신 |
| `pick_place` | object_id, slot_id | 대상 존재, 목표 칸 비어 있음, 좌표가 작업 범위 안 | 행동 후 대상이 목표 칸에 있음 |
| `hand_over` | object_id | 전달 위치(H) 비어 있음 | 대상이 H에 있음 |
| `optimize_layout` | 없음 | 사용 기록 존재 | 칸 배정표 반환 |
| `verify_result` | goal_id | 최신 영상 | 목표 조건과 일치 |
| `ask_user` | question | 모호·정보 부족 | 사용자 응답 수신 |

공통 반환 `status`: `SUCCESS` / `FAILED` / `UNAVAILABLE` / `HOLD`

## 5. 시퀀스 다이어그램

### 5-1. 작업 중 보조: "저항 줘"

```mermaid
sequenceDiagram
    actor User as 작업자
    participant App as Action Manager
    participant Vision
    participant Planner as GenAI Planner
    participant Gate as Safety Gate
    participant Arm as SO-101

    User->>App: "저항 줘"
    App->>Vision: 최신 상태 요청
    Vision-->>App: WorldState
    App->>Planner: 목표 + WorldState + Skill 목록
    Planner-->>App: Plan JSON
    App->>Gate: validate(Plan, WorldState)
    alt 후보가 여러 개
        Gate-->>App: 질문 필요
        App-->>User: "220Ω, 1kΩ 중 어느 거요?"
        User->>App: "1kΩ"
        App->>Planner: 답변 반영해 재계획
        Planner-->>App: Plan JSON
        App->>Gate: validate
    end
    alt 통과
        Gate-->>App: OK
        App->>Arm: hand_over(resistor_1k)
        Arm-->>App: 동작 완료
        App->>Vision: 결과 확인
        Vision-->>App: H 칸에 저항 있음
        App-->>User: "전달 위치에 놓았어요"
    else 거절
        Gate-->>App: 거절 + 이유
        App-->>User: 이유 안내 (실행 안 함)
    end
```

### 5-2. 작업 후 정리: "정리해 줘"

```mermaid
sequenceDiagram
    actor User as 작업자
    participant App as Action Manager
    participant Vision
    participant LO as Layout Optimizer
    participant Log as 사용 기록
    participant Gate as Safety Gate
    participant Arm as SO-101

    User->>App: "정리해 줘"
    App->>Vision: 작업 구역 물건 인식
    Vision-->>App: WorldState
    App->>Log: 사용 빈도 · 함께 쓴 물건 · 다음 작업
    Log-->>App: 사용 통계
    App->>LO: assign(물건, 빈 칸, 통계)
    LO-->>App: 칸 배정표 + 예상 거리
    loop 물건마다
        App->>Gate: pick_place 검증
        Gate-->>App: OK
        App->>Arm: pick_place(object, slot)
        Arm-->>App: 완료
        App->>Vision: 결과 확인
        alt 실패
            App->>App: 재시도 (최대 2회) 후 HOLD
        end
    end
    App->>Log: 정리 결과 기록
    App-->>User: 정리 완료 + 전후 거리 비교
```

## 6. 상태 다이어그램: 실행 FSM

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> OBSERVE: 명령 수신
    OBSERVE --> PLAN: 상태 갱신
    PLAN --> VALIDATE: 계획 생성
    PLAN --> ASK: 모호함
    ASK --> PLAN: 사용자 응답
    VALIDATE --> EXECUTE: 통과
    VALIDATE --> IDLE: 거절 (이유 안내)
    EXECUTE --> VERIFY: 동작 완료
    VERIFY --> OBSERVE: 다음 단계 남음
    VERIFY --> DONE: 목표 달성
    VERIFY --> REPLAN: 실패
    REPLAN --> VALIDATE: 재시도 예산 안
    REPLAN --> HOLD: 재시도 초과
    HOLD --> IDLE: 사람 확인
    DONE --> IDLE

    state "ESTOP (어느 상태에서든)" as ESTOP
    EXECUTE --> ESTOP: 비상 정지
    ESTOP --> IDLE: 수동 재시작
```

## 7. 범용성을 만드는 구조

```mermaid
flowchart LR
    subgraph Fixed[고정: 엔진 코드]
        E[Planner · Safety Gate · Action Manager<br/>Optimizer · Skill 구현]
    end
    subgraph Swap[교체: 데이터만]
        T1[tasks/led_lab.yaml<br/>전자회로 실습]
        T2[tasks/color_class.yaml<br/>색깔 수업]
        T3[tasks/새 작업.yaml]
        OBJ[objects.yaml<br/>물건 목록]
    end
    T1 --> E
    T2 --> E
    T3 -.추가.-> E
    OBJ --> E
```

새 작업을 추가할 때 **엔진 코드는 바꾸지 않고**, 작업 설명서와 물건 목록만 추가합니다. 이때 걸린 시간과 코드 수정 줄 수를 측정해 규칙 기반 방식(작업마다 동작 코드를 새로 작성)과 비교합니다 ([vision.md H1](vision.md)).

작업 설명서 예시 (초안):

```yaml
task_id: led_lab
name: LED 회로 실습
required_objects: [breadboard, led_red, resistor_220, jumper_wires, battery_holder]
notes: 저항은 LED 바로 옆에 둔다
```

## 8. 안전 설계

| 위험 | 대응 |
|---|---|
| LLM이 잘못된 계획을 냄 | JSON schema 제약 출력, 등록된 Skill·물건만 허용, 좌표 범위 검사, 재시도 횟수 제한 |
| 사람이 작동 영역에 손을 넣음 | 로봇이 멈춘 뒤에만 물건 변경, 저속 운전, 물리적 비상 정지. **카메라 감지만으로 안전을 보장하지 않음** |
| 좌표 오차로 물건 떨어뜨림 | 고정 지그·칸, 가벼운 물체, 보정 후 오차 측정, 행동 후 결과 확인 |
| 장치 통신 끊김 | 시간 제한, watchdog, 안전 정지 |

## 9. 폴더 구조 (예정)

```text
Thursday/
├── app/
│   ├── ui/          # Streamlit 대시보드, CLI
│   ├── core/        # WorldState, Planner, SafetyGate, ActionManager, Optimizer
│   ├── vision/      # 인식, 좌표 변환
│   ├── skills/      # Skill 구현 (pick_place, hand_over ...)
│   └── hw/          # SO-101·카메라 접근 (실제 + mock)
├── tasks/           # 작업 설명서 (*.yaml)
├── config/          # 물건 목록, 칸 좌표, 보정값
├── tests/           # pytest (하드웨어는 mock)
├── docs/            # 이 문서들
└── requirements.txt
```
