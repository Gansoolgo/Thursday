# 협업 안내 (GitHub로 같이 일하는 법)

4명이 같은 저장소에서 서로의 작업을 덮어쓰지 않고 일하기 위한 규칙입니다.
처음이면 **[한 장 요약](#한-장-요약)** 만 읽고 시작해도 됩니다.

> 이 문서는 **팀 공통 규칙**입니다. 맡은 Issue를 각자 어떻게 개발할지(어떤 AI를 쓸지, 서브 에이전트를 쓸지 등)는 자유입니다.
> 단, AI를 쓸 때도 [AGENTS.md](AGENTS.md)의 공통 규칙은 지킵니다.

---

## 한 장 요약

```text
1. Issue 고르기      → 담당자에 내 이름, 댓글 "제가 할게요"
2. 브랜치 만들기     → main 최신화 후 feature/US-03-hand-over
3. 작업·커밋         → "US-03: hand_over Skill 추가 (#10)"
4. push·PR 열기      → PR 본문에 "Closes #10", 체크리스트 채우기
5. 리뷰 받기         → Reviewers에 1명 지정, 승인 + CI 통과 (리뷰 기준은 5장)
6. 병합              → Squash and merge, 브랜치 삭제
7. 내 PC 정리        → main으로 돌아가 pull
```

## 1. Issue 고르기

- [Issues](https://github.com/Gansoolgo/Thursday/issues)에서 이번 스프린트 Milestone의 Issue를 고릅니다.
- **Assignees에 자기 이름을 넣습니다.** 담당자가 있는 Issue는 다른 사람이 손대지 않습니다.
- 새로 할 일이 생기면 Issue를 먼저 만듭니다(템플릿 선택). 말로만 하고 코드부터 짜지 않습니다.
- Issue 하나는 **1~2일 안에 끝낼 크기**로 합니다. 더 크면 나눕니다.

## 2. 브랜치 만들기

`main`에는 직접 push하지 않습니다. 항상 브랜치에서 작업합니다.

```powershell
git switch main
git pull
git switch -c feature/US-03-hand-over
```

| 종류 | 이름 형식 | 예시 |
|---|---|---|
| 기능 | `feature/<스토리ID 또는 Issue번호>-<짧은설명>` | `feature/US-03-hand-over` |
| 기술 검증 | `spike/<Issue번호>-<설명>` | `spike/6-llm-json` |
| 버그 | `fix/<Issue번호>-<설명>` | `fix/12-calib-offset` |
| 문서 | `docs/<Issue번호>-<설명>` | `docs/8-interfaces` |
| 설정·기타 | `chore/<설명>` | `chore/ci` |

## 3. 커밋

- 의미 있는 단위로 자주 커밋합니다.
- 메시지 형식: `<스토리ID 또는 종류>: <무엇을 했는지> (#Issue번호)`
  - `US-03: hand_over Skill 추가 (#10)`
  - `spike: Qwen3-4B JSON 계획 응답 시간 측정 (#6)`
- **커밋하면 안 되는 것:** API 키·비밀번호, `.env`, 모델 파일(`.bin`, `.onnx` 등), 큰 데이터. [.gitignore](.gitignore)에 대부분 막혀 있습니다.
- AI로 만든 코드는 커밋 메시지 끝에 `Co-Authored-By:` 줄이나 PR 본문에 사용한 도구를 남깁니다.

## 4. push와 PR 열기

```powershell
git push -u origin feature/US-03-hand-over
```

GitHub에서 **Compare & pull request**를 누르면 PR 템플릿이 뜹니다.
- 본문에 `Closes #10`을 쓰면 병합할 때 Issue가 자동으로 닫힙니다.
- 체크리스트(DoD)를 채웁니다. 해당 없는 항목은 `해당 없음`이라고 적습니다.
- 아직 덜 됐지만 의견을 받고 싶으면 **Draft PR**로 엽니다.
- **PR은 작게.** 변경이 400줄을 넘으면 나눌 수 있는지 먼저 봅니다.

## 5. 리뷰

리뷰는 **"이걸 main에 넣어도 팀이 곤란해지지 않는가?"** 를 판단하는 일입니다. 완벽한 코드인지 따지는 자리가 아닙니다.

- **다른 팀원 1명 이상의 승인(Approve)** 이 있어야 병합합니다. (작성자는 자기 PR을 승인할 수 없습니다)
- PR 작성자가 오른쪽 **Reviewers**에서 1명을 지정합니다. 그 모듈의 결과를 받아 쓰는 사람이 좋습니다 (예: Vision PR → GenAI 담당).
- 리뷰어는 **하루 안에** 봅니다. 급하면 Discord에서 부릅니다.

### 5-1. 리뷰 순서 (PR 하나에 10~20분)

| 순서 | 어디서 | 무엇을 |
|---|---|---|
| ① 목적 | PR 본문, 연결된 Issue | 무엇을 왜 했나? Issue의 인수 조건은? |
| ② 자동 검사 | PR 아래 **Checks** | CI가 초록색인가? 빨간색이면 더 볼 필요 없이 "고쳐 주세요" |
| ③ 범위 | **Files changed** 탭의 파일 목록 | Issue와 상관없는 파일이 바뀌지 않았나? 400줄이 넘으면 나눌 수 있나? |
| ④ 내용 | Files changed 탭에서 한 줄씩 | 아래 5-2 체크 항목 |
| ⑤ 직접 확인 | PR 본문의 "확인 방법" | 중요한 PR이면 브랜치를 받아 직접 실행 (`git fetch` → `git switch <브랜치>`) |
| ⑥ 결정 | **Review changes** 버튼 | 아래 5-3 기준으로 하나 선택 |

### 5-2. 꼭 볼 것

**모든 PR**
- [ ] PR 템플릿 체크리스트(DoD)가 채워져 있다
- [ ] 비밀값(키·비밀번호), `.env`, 모델 파일·큰 데이터가 없다

**코드 PR**
- [ ] [docs/interfaces.md](docs/interfaces.md) 형식을 지켰다 — 단위 mm, dataclass 이름·필드. **여기가 틀리면 M3 통합 때 터집니다**
- [ ] 테스트가 있고, 하드웨어는 mock으로 테스트했다
- [ ] 공통 파일(`app/core/types.py`, `config/*.yaml`)을 바꿨다면 이유가 PR에 있다

**로봇·LLM PR (가장 엄격하게)**
- [ ] LLM 출력이 Safety Gate를 거치지 않고 로봇으로 가는 경로가 없다
- [ ] 새 동작의 기본값이 저속이고 작업 영역 제한이 있다
- [ ] 비상 정지(`stop()`)가 어떤 상태에서도 동작한다
- [ ] 실제 로봇으로 시험했다면 결과(영상, N회 중 성공 횟수)가 있다

**문서 PR**
- [ ] 사실과 맞고, 다른 문서와 서로 어긋나지 않는다

### 5-3. 결정 기준

| 결정 | 언제 | 예시 |
|---|---|---|
| ✅ **Approve** (승인) | 위 항목에 문제가 없음. 사소한 취향 차이는 의견만 남기고 승인 | "변수명은 취향 차이라 그대로 둬도 돼요" |
| 🔄 **Request changes** (수정 요청) | **이대로 넣으면 문제가 생김** | CI 실패, 인터페이스 위반, 안전 경로 누락, 비밀값 포함, 실행 안 됨 |
| 💬 **Comment** (의견만) | 판단이 애매하거나 질문만 있음 | "이 부분은 왜 이렇게 했어요?" |

> **기준:** "내가 짰으면 다르게 했을 것"은 수정 요청 사유가 아닙니다. **"이대로 넣으면 문제가 생긴다"** 만 수정 요청 사유입니다.

### 5-4. 코멘트 주고받기

- **리뷰어:** Files changed에서 해당 줄 왼쪽의 `+`를 눌러 그 줄에 의견을 남깁니다. "~하면 어떨까요?"처럼 제안형으로, 이유를 함께 씁니다.
- **작성자:** 같은 브랜치에 커밋을 추가해 push하면 PR이 자동으로 갱신됩니다. 코멘트마다 "반영했어요(커밋 abc123)" 또는 "이래서 그대로 둘게요"라고 답하고 **Resolve conversation**을 누릅니다.
- 수정 후 다시 봐 달라고 할 때는 Reviewers 옆 🔄(Re-request review)를 누릅니다.
- AI(Codex, Claude)로 먼저 훑어보는 건 좋습니다. 하지만 **승인 버튼은 사람이 내용을 이해한 뒤에** 누릅니다.

### 5-5. 우회 병합

4명 모두 조직 owner라 보호 규칙을 우회해 병합할 수 있습니다. **우회 병합은 급할 때만** 쓰고, 썼으면 Discord에 이유를 남깁니다.

## 6. 병합과 정리

- CI 통과 + 승인 1명 → **Squash and merge** (커밋을 하나로 합쳐 main 기록을 깔끔하게) → **Delete branch**.
- 병합 후 내 PC 정리:

```powershell
git switch main
git pull
git branch -d feature/US-03-hand-over
```

## 7. 충돌이 났을 때

다른 사람이 먼저 병합해서 같은 파일이 바뀐 경우입니다.

```powershell
git switch main
git pull
git switch feature/US-03-hand-over
git merge main
# 충돌 파일을 열어 <<<<<<< ======= >>>>>>> 부분을 고친 뒤
git add <파일>
git commit
git push
```

모르겠으면 혼자 해결하지 말고 해당 파일을 마지막으로 고친 사람과 같이 봅니다.
**공통 파일**(`app/core/types.py`, `docs/interfaces.md`, `config/*.yaml`)은 충돌이 잦으니, 바꾸기 전에 Discord에 먼저 알립니다.

## 8. 로봇은 한 대

- 로봇을 쓰기 전에 Discord에 "로봇 사용 14:00~15:00 (#10)"처럼 남깁니다.
- 로봇이 없을 때는 `MockRobotArm`([interfaces.md 5장](docs/interfaces.md#5-skill과-실행-결과))으로 개발·테스트합니다.
- 실제 로봇 시험 순서: **mock 테스트 → 저속·제한 동작 → 정상 속도.** 작동 중에는 작업 영역에 손을 넣지 않습니다.
- 보정값·칸 좌표(`config/slots.yaml`)를 바꿨으면 PR로 올리고 Discord에 알립니다. 다른 사람 결과가 달라지기 때문입니다.

## 9. 스프린트 리듬

자세한 일정은 [docs/workflow.md](docs/workflow.md)에 있습니다.

| 언제 | 무엇 | 시간 |
|---|---|---|
| 스프린트 첫날 | 계획: 이번에 끝낼 Issue 고르기, 담당 지정 | 15분 |
| 매일 | Discord에 한 줄: 어제 한 것 / 오늘 할 것 / 막힌 것 | 1분 |
| 스프린트 마지막 날 | 시연: 병합된 것을 실제 로봇으로 돌려 보기 | 20분 |
| 스프린트 마지막 날 | 회고: 잘된 점 / 아쉬운 점 / 다음에 바꿀 점 | 5분 |

## 10. 자주 쓰는 명령

| 하고 싶은 것 | 명령 |
|---|---|
| 지금 상태 보기 | `git status` |
| 최신 main 받기 | `git switch main` → `git pull` |
| 바뀐 내용 보기 | `git diff` |
| 커밋 | `git add <파일>` → `git commit -m "US-03: ... (#10)"` |
| 브랜치 목록 | `git branch` |
| 마지막 커밋 메시지 고치기(push 전) | `git commit --amend` |
