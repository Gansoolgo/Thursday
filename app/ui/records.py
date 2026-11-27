"""Thursday 한방 — 공통 저장 (Issue #46).

모든 화면 아래 "저장 줄"이 쓰는 함수 모음입니다.
- append(): logs/<kind>.jsonl 에 한 줄(JSON 하나) 추가
  (interfaces.md 0장: 로그는 .jsonl, logs/ 는 Git 제외)
- read():   그 파일을 다시 읽기 (작업 이름으로 거르기 가능)
- draft_md(): docs/records/templates/experiment.md 양식의 실험 기록 초안 글자 만들기
              모르는 칸은 "(확인 필요)" 로 둔다 (숫자를 지어내지 않는다)
"""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

TBD = "(확인 필요)"
_KIND_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")  # 파일 이름으로 쓰므로 안전한 글자만


def _file(kind: str, log_dir: str | Path) -> Path:
    if not _KIND_RE.match(kind):
        raise ValueError(f"기록 종류 이름이 규칙에 안 맞습니다: {kind!r} (영어 소문자·숫자·_)")
    return Path(log_dir) / f"{kind}.jsonl"


def append(
    kind: str, task_id: str, data: dict, tag: str = "", log_dir: str | Path = "logs"
) -> dict:
    """기록 한 줄을 추가하고, 추가한 줄(dict)을 돌려준다."""
    path = _file(kind, log_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"t": time.time(), "task_id": task_id, "tag": tag.strip(), "data": data}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read(kind: str, task_id: str | None = None, log_dir: str | Path = "logs") -> list[dict]:
    """기록을 읽는다. task_id 를 주면 그 작업 것만, 파일이 없으면 빈 목록."""
    path = _file(kind, log_dir)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if task_id is None or row.get("task_id") == task_id:
            rows.append(row)
    return rows


def draft_md(
    title: str,
    purpose: str = "",
    rows: list[tuple[str, str]] | None = None,
    source: str = "",
    method: str = "",
) -> str:
    """실험 기록 초안(마크다운). 비운 칸은 모두 "(확인 필요)"."""
    table = "\n".join(f"| {name} | {value} |" for name, value in (rows or [])) or f"| {TBD} | |"
    return f"""# 실험 기록: {title}

- **날짜:** {date.today().isoformat()}
- **작성자:** {TBD}
- **관련 Issue:** # {TBD}
- **결과 한 줄:** {TBD}

## 1. 목적
{purpose or TBD}

## 2. 환경
| 항목 | 값 |
|---|---|
| 장치 | {TBD} |
| OS | Windows 11 (빌드 {TBD}) |
| 주요 버전 | {TBD} |
| 모델 | {TBD} |
| 하드웨어 상태 | {TBD} |

## 3. 방법
{method or "Thursday 한방에서 시험 " + TBD}

## 4. 결과
| 지표 | 값 |
|---|---|
{table}

- 원본 기록: {source or TBD}
- 사진·영상: (공유 폴더 경로 {TBD})

## 5. 잘 안 된 것과 원인
{TBD}

## 6. 결론과 다음 할 일
- **결론:** {TBD}
- **다음:** {TBD}
- results-m1.md / decisions.md 반영: 안 함
"""
