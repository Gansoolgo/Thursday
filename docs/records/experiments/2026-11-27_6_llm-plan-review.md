# 실험 기록: Issue #6 채점과 결과 요약 검증

- **날짜:** 2026-11-27
- **작성자:** Codex
- **관련 Issue:** #6
- **결과 한 줄:** 기존 테스트 9개 통과. 추가 입력에서 채점 오류와 Windows 요약 출력 오류 재현.

## 1. 목적

형식이 잘못된 계획과 대상이 틀린 확인 단계의 채점 및 저장된 결과의 요약을 확인한다.

## 2. 환경

Windows, 저장소 `.venv`. 모델 재실행 없음. 전원 상태는 (확인 필요).

## 3. 방법

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe spikes\llm_plan.py --summary outputs\llm_plan\results_v4_20261127.jsonl
.venv\Scripts\python.exe -X utf8 spikes\llm_plan.py --summary outputs\llm_plan\results_v4_20261127.jsonl
```

`runpy.run_path("spikes/llm_plan.py")["grade"]`에 `question=true`인 되묻기, `steps=null`인 실행, 정상 전달에 다른 물건을 확인하는 단계가 붙은 실행을 넣었다. 저장된 Qwen3-4B GPU·CPU 응답은 현재 채점기로 각각 다시 채점했다.

## 4. 결과

- Ruff: `All checks passed!`
- pytest: `9 passed in 0.03s`
- 질문 값이 불리언인 경우와 확인 대상이 다른 경우에 `json=True, decision=True, target=True`가 나왔다.
- 기존 채점 로직으로 원본을 다시 집계한 결과 GPU 16/16, CPU 8/8, 위험 실행 0이다. 튜닝 문장 결과다.

## 5. 잘 안 된 것과 원인

- `steps=null` → `TypeError: 'NoneType' object is not iterable`
- 기본 요약 명령 → `UnicodeEncodeError: 'cp949' codec can't encode character '\u2014' in position 57: illegal multibyte sequence`. `-X utf8`으로 실행하면 요약이 출력됐다.

## 6. 결론과 다음 할 일

- 형식과 확인 대상을 검사하고 반복마다 정답·위험 실행을 채점한 뒤 정식 20문장 평가를 진행한다.
- results-m1.md 반영: 정식 모델 시험 결과가 없어 갱신하지 않았다.

## 7. 수정 후 재검증

- `.venv\Scripts\python.exe -m ruff check .` → `All checks passed!`
- `.venv\Scripts\python.exe -m pytest -q` → `58 passed in 0.35s`
- `.venv\Scripts\python.exe spikes\llm_plan.py --summary outputs\llm_plan\results_dev20_20261127.jsonl` → 종료 0.
- `load_commands`로 읽은 정답으로 저장된 응답을 `grade`에 다시 넣었다. Qwen3-4B GPU 29/40(되묻기→실행 4, 거절→실행 1), CPU 26/40(되묻기→실행 4). GPU 평균/최대 4.4/5.6초, CPU 4.4/5.5초. 모델 재실행 없음.
- 전달 이전에 결과를 확인하는 순서의 계획을 `grade`에 넣으면 `target=True`가 나왔다.

## 8. 규칙과 모델을 함께 쓰는 방식 검증

- `.venv\Scripts\python.exe -m pytest -q` → `82 passed in 0.17s`.
- `.venv\Scripts\python.exe spikes\llm_plan.py --summary outputs\llm_plan\results_hybrid_20261127.jsonl` → Qwen3-4B CPU·GPU 각각 40/40, 규칙 처리 36/40, 평균 0.4초. 모델 호출 평균 CPU 3.9초, GPU 4.2초.
- `runpy.run_path("spikes/llm_plan.py")["rule_plan"]`에 ‘T 조각 말고 L 조각 줘’와 ‘T 조각 A1에 놓지 말아 줘’를 입력했다. 전자는 두 조각 모두 `hand_over`, 후자는 `pick_place`를 반환했다.
