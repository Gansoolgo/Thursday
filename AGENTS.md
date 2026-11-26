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

## Git

- `main`에 직접 push하지 않는다. 브랜치 이름과 커밋 형식은 [CONTRIBUTING.md](CONTRIBUTING.md)를 따른다.
- PR은 [템플릿](.github/pull_request_template.md)의 DoD 체크리스트를 채운다. 병합은 사람이 한다.
- AI가 작성한 커밋에는 `Co-Authored-By:` 줄을 남긴다.

## 코드 스타일

- 폴더 구조는 `docs/architecture.md` 9장을 따른다 (`app/core`, `app/vision`, `app/skills`, `app/hw`, `app/ui`).
- 린트: Ruff (`pyproject.toml` 설정). 테스트: pytest (`tests/`).
- 주석·문서·커밋 메시지는 한국어, 코드 식별자는 영어.
- 단순하게: 단일 Python 프로세스 + 함수 호출. 필요가 확인되기 전에는 서버·메시지 큐를 추가하지 않는다.
