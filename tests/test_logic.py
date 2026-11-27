"""Thursday 한방 공통 로직 테스트 (명령 해석 · 안전 검사 · 통계 · 판단 · 자율 모드 시나리오)."""

import random

from app.ui import logic as lg
from app.ui import slots as sl


# ---- 말 → 명령 ----
def test_parse_color_request():
    assert lg.parse_cmd("노랑 블록 줘")["cmd"] == "hand_over(block_yellow)"
    assert lg.parse_cmd("파란 거 건네줘")["cmd"] == "hand_over(block_blue)"


def test_parse_stop_and_ambiguous_and_unknown():
    assert lg.parse_cmd("멈춰")["skill"] == "stop"
    assert lg.parse_cmd("블록 줘")["amb"] is True
    assert lg.parse_cmd("오늘 날씨 어때") is None


# ---- 안전 검사 (H5) ----
def test_gate_blocks_every_dangerous_request():
    for s in lg.GATE_BAD:
        assert lg.gate_check(s)["v"] != "OK", s


def test_gate_false_reject_on_normal_requests_is_small():
    rejected = [s for s in lg.GATE_OK if lg.gate_check(s)["v"] == "REJECT"]
    assert len(rejected) <= 2  # evaluation.md 목표: 잘못된 거절 2개 이하


def test_gate_estop_rejects_at_check_1():
    g = lg.gate_check("노랑 블록 줘", estop=True)
    assert (g["v"], g["at"], g["code"]) == ("REJECT", 1, "ESTOP")


def test_gate_ambiguous_asks_at_check_5():
    g = lg.gate_check("블록 줘")
    assert (g["v"], g["at"], g["code"]) == ("ASK", 5, "AMBIGUOUS")


# ---- 통계 ----
def test_wilson_interval_for_18_of_20():
    lo, hi = lg.wilson(18, 20)
    assert round(lo * 100) == 70 and round(hi * 100) == 97
    assert lg.pct_ci(0, 0) == "측정 전"
    assert lg.pct_ci(18, 20).startswith("90% (70~97%)")


def test_median_and_p95():
    assert lg.median([3, 1, 2]) == 2
    assert lg.median([1, 2, 3, 4]) == 2.5
    assert lg.p95(list(range(1, 21))) == 19
    assert lg.median([]) is None


# ---- 판단 규칙 ----
def test_hand_over_choice_d08():
    assert lg.hand_choice("in") == "on_hand"
    assert lg.hand_choice("out") == "slot_H"
    assert lg.hand_choice("none") == "slot_H"
    assert lg.hand_choice("move") == "stop"


def test_cloth_steps_d07():
    assert lg.cloth_steps("flat") == ["fold_half", "fold_half"]
    assert lg.cloth_steps("c1") == ["unfold_corner", "fold_half", "fold_half"]
    assert lg.cloth_steps("crumpled") == []


def test_progress_detects_deviation_and_keep_reorders():
    p = lg.new_progress(["blue", "yellow", "red", "green", "orange", "white"])
    assert lg.place(p, "blue")["k"] == "진행"
    ev = lg.place(p, "orange")
    assert ev["k"] == "이탈" and p["ask"] == {"c": "orange", "exp": "yellow"}
    lg.answer(p, "keep")
    assert [x["c"] for x in p["placed"]] == ["blue", "orange"]
    assert p["order"][2:].count("yellow") == 1  # 노랑은 남은 순서 안에 남아 있음
    assert p["ask"] is None


def test_layout_fused_is_not_worse_than_fixed():
    objs = [("block_blue", "small", 9), ("block_red", "small", 1), ("block_tray", "big", 5)]
    res = lg.compare_layouts(objs, sl.default_slots(), sl.ROBOTS, alpha=0.7, beta=0.3)
    assert set(res) == {"fixed", "usage", "space", "fused"}
    assert res["fused"]["cost"] <= res["fixed"]["cost"]
    assert len(set(res["fused"]["assign"].values())) == 3  # 한 칸에 하나씩


# ---- 자율 모드 시나리오 (99) ----
def test_build_act_checks_safety_before_acting():
    steps = lg.build_act("say_start", "block_a", random.Random(1))["steps"]
    kinds = [s["k"] for s in steps]
    assert kinds.index("gate") < kinds.index("act")


def test_dangerous_request_is_rejected_without_action():
    b = lg.build_act("say_bad", "block_a", random.Random(1))
    assert b["res"] == "REJECT"
    assert "act" not in [s["k"] for s in b["steps"]]


def test_session_stats():
    ev = [{"res": "OK", "asked": 1, "total": 3000}, {"res": "REJECT", "asked": 0, "total": None}]
    st = lg.session_stats(ev)
    assert st["events"] == 2 and st["ok"] == 1 and st["asked"] == 1 and st["median"] == 3000
