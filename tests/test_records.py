"""Thursday 한방 공통 저장(records) 테스트 — Issue #46 완료 조건 1·2."""

import json

import pytest

from app.ui import records

SECTIONS = [
    "## 1. 목적",
    "## 2. 환경",
    "## 3. 방법",
    "## 4. 결과",
    "## 5. 잘 안 된 것과 원인",
    "## 6. 결론과 다음 할 일",
]


def test_append_twice_writes_two_lines_and_read_filters_task(tmp_path):
    records.append("mic", "block_a", {"heard": "노랑 블록 줘"}, tag="1차", log_dir=tmp_path)
    records.append("mic", "fold_cloth", {"heard": "손수건 개 줘"}, log_dir=tmp_path)

    lines = (tmp_path / "mic.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["data"]["heard"] == "노랑 블록 줘"  # 한글이 그대로 저장됨

    rows = records.read("mic", "block_a", log_dir=tmp_path)
    assert len(rows) == 1
    assert rows[0]["task_id"] == "block_a"
    assert rows[0]["tag"] == "1차"
    assert isinstance(rows[0]["t"], float)  # interfaces.md 0장: time.time() 실수 초

    assert len(records.read("mic", log_dir=tmp_path)) == 2  # task_id 없으면 전부


def test_read_missing_file_returns_empty_list(tmp_path):
    assert records.read("nothing_yet", log_dir=tmp_path) == []


def test_kind_must_be_a_safe_file_name(tmp_path):
    with pytest.raises(ValueError):
        records.append("../outside", "block_a", {}, log_dir=tmp_path)


def test_draft_md_follows_experiment_template():
    md = records.draft_md(
        "block_a · 마이크·음성",
        purpose="",
        rows=[("음성 명령 정확도", "9/10")],
        source="logs/mic.jsonl",
    )
    assert md.startswith("# 실험 기록: block_a · 마이크·음성")
    for head in SECTIONS:
        assert head in md
    assert "(확인 필요)" in md  # 비운 칸
    assert "| 음성 명령 정확도 | 9/10 |" in md
    assert "logs/mic.jsonl" in md
