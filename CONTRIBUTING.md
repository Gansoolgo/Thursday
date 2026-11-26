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
5. 리뷰 받기         → 다른 팀원 1명 승인 + CI 통과
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

- **다른 팀원 1명 이상의 승인(Approve)** 이 있어야 병합합니다.
- 리뷰어는 하루 안에 봅니다. 급하면 Discord에서 부릅니다.
- 리뷰에서 보는 것:
  1. Issue의 인수 조건을 만족하는가
  2. [docs/interfaces.md](docs/interfaces.md)의 데이터 형식·함수 모양을 지켰는가
  3. 하드웨어 코드라면 mock 테스트가 있고, 실제 로봇은 저속으로 먼저 시험했는가
  4. 비밀값·큰 파일이 없는가
- 의견은 "이렇게 바꾸면 어떨까요?"처럼 제안으로 남기고, 작성자는 반영하거나 반영하지 않는 이유를 답합니다.

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
