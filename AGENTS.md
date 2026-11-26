# AI 에이전트 공통 규칙

이 저장소에서 코드를 만들거나 고치는 AI(Claude Code, Codex 등)가 따라야 할 규칙입니다. 팀원 4명이 각자 다른 AI·방식으로 개발해도 결과물이 서로 맞물리게 하는 최소한의 약속입니다.

## 프로젝트

Thursday — 작업실 AI 조수 로봇팔. 사용자 말 → 로컬 LLM 계획(JSON) → Safety Gate 검증 → SO-101 로봇팔 실행 → 카메라로 결과 확인.
먼저 읽을 것: [README.md](README.md), [docs/architecture.md](docs/architecture.md), [docs/interfaces.md](docs/interfaces.md), [CONTRIBUTING.md](CONTRIBUTING.md)

## 환경

- OS: Windows 11 (PowerShell). 경로·명령은 Windows 기준으로 작성한다.
- Python 3.12, 프로젝트별 venv, `requirements.txt`에 버전 고정.
- 하드웨어: Intel Core Ultra 5 225H (CPU·iGPU·NPU), SO-101, 웹캠. 인터넷 없이 동작해야 한다.

## 반드시 지킬 것

1. **LLM은 모터를 직접 움직이지 않는다.** LLM 출력은 `docs/interfaces.md` 3장의 Plan JSON뿐이고, Safety Gate를 거친 뒤 등록된 Skill만 실행한다. LLM이 Gate 규칙을 바꿀 수 있는 경로를 만들지 않는다.
2. **인터페이스를 지킨다.** 모듈 사이 데이터는 `docs/interfaces.md`의 형식(단위 mm, 좌표계 `table`, dataclass 이름·필드)을 따른다. 바꿔야 하면 코드와 문서를 같은 PR에서 고치고 PR 본문에 명시한다.
3. **하드웨어는 감싸고 mock을 둔다.** 카메라·로봇 접근은 `app/hw/`에만 두고, 같은 모양의 mock 구현을 함께 만든다. 테스트는 mock으로 돌린다.
4. **실제 로봇을 움직이는 코드는 사람이 실행한다.** AI가 로봇을 움직이는 명령을 직접 실행하지 않는다. 새 동작은 저속·작업 영역 제한을 기본값으로 둔다. 비상 정지(`stop()`)는 어떤 상태에서도 동작해야 한다.
5. **비밀값을 코드·로그·커밋에 넣지 않는다.** 필요하면 OS 비밀 저장소(Windows 자격 증명 관리자)에서 실행 시 읽는다. 모델 파일과 큰 데이터는 커밋하지 않는다.
6. **맡은 범위만 고친다.** 작업 중인 Issue와 무관한 파일, 특히 공통 파일(`app/core/types.py`, `docs/interfaces.md`, `config/*.yaml`)은 필요할 때만 최소로 고치고 PR에 이유를 적는다.
7. **실행하지 않은 테스트를 통과했다고 하지 않는다.** 보고할 때 실제 실행한 것과 하지 않은 것을 구분한다.

## 작업 지시를 받으면

팀원은 [docs/ai-guide.md](docs/ai-guide.md)의 **Issue 명세 6칸**(목표 · 입력/출력 · 수정할 파일 · 건드리지 말 것 · 완료 조건 · 확인 방법)으로 지시합니다.

- **③ 수정할 파일** 밖의 파일을 바꿔야 하면, 바꾸지 말고 먼저 이유와 함께 묻는다.
- **④ 건드리지 말 것**은 어떤 이유로도 어기지 않는다.
- **⑤ 완료 조건**은 테스트로 옮기고, 그 테스트를 실제로 실행해 결과 원문을 보여 준다.
- 명세가 모호하거나 `docs/interfaces.md`와 맞지 않으면 추측해서 채우지 말고 질문한다.
- "계획만" 요청을 받으면 코드를 쓰지 않는다.

## 작업이 끝나면 기록 초안을 쓴다

사람은 기록을 자주 잊습니다. 그래서 **AI가 먼저 챙깁니다.** ([기록 가이드](docs/records.md))

- 무언가를 **시험·측정**했으면: [실험 기록 양식](docs/records/templates/experiment.md)으로 `docs/records/experiments/날짜_Issue번호_내용.md` **초안을 만든다.** 실제로 실행한 명령·결과 숫자·에러 원문만 쓰고, 모르는 칸은 `(확인 필요)`로 남긴다. 숫자를 지어내지 않는다.
- **사진·녹음 등 데이터**를 모으거나 바꿨으면: [데이터 카드 양식](docs/records/templates/data-card.md)으로 `docs/records/data/` 초안을 만든다.
- **M1 Issue**라면 [results-m1.md](docs/plan/results-m1.md)의 해당 칸에 숫자를 채운다.
- 초안을 만든 뒤 사람에게 **"기록 초안을 만들었어요. 숫자와 결론을 확인해 주세요"** 라고 알린다.
- 시험이 없는 작업(문서·설정 등)이면 기록 초안은 만들지 않는다.

## Git

- `main`에 직접 push하지 않는다. 브랜치 이름과 커밋 형식은 [CONTRIBUTING.md](CONTRIBUTING.md)를 따른다.
- PR은 [템플릿](.github/pull_request_template.md)의 DoD 체크리스트를 채운다. 병합은 사람이 한다.
- AI가 작성한 커밋에는 `Co-Authored-By:` 줄을 남긴다.

## 코드 스타일

- 폴더 구조는 `docs/architecture.md` 9장을 따른다 (`app/core`, `app/vision`, `app/skills`, `app/hw`, `app/ui`).
- 린트: Ruff (`pyproject.toml` 설정). 테스트: pytest (`tests/`).
- 주석·문서·커밋 메시지는 한국어, 코드 식별자는 영어.
- 단순하게: 단일 Python 프로세스 + 함수 호출. 필요가 확인되기 전에는 서버·메시지 큐를 추가하지 않는다.
