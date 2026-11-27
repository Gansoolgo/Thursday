"""#6 spikes/llm_plan.py 채점 로직 테스트 (모델 없이 돈다).

GPT 검증(REVIEW) 요청: 형식·판단·대상을 따로 채점하고, 형식은 맞지만 뜻이 틀린 출력을 실패로 본다.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPIKE = Path(__file__).resolve().parents[1] / "spikes" / "llm_plan.py"


@pytest.fixture(scope="module")
def lp(monkeypatch_module):
    # 스크립트가 불러올 때 명령줄 인자를 읽으므로 pytest 인자 대신 빈 인자를 준다
    monkeypatch_module.setattr(sys, "argv", ["llm_plan.py"])
    spec = importlib.util.spec_from_file_location("llm_plan", SPIKE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def plan(decision, steps=(), question=None, reason=None):
    return json.dumps({"decision": decision, "goal": "g", "task_id": None, "steps": list(steps),
                       "question": question, "reason": reason}, ensure_ascii=False)


def step(skill, obj, slot):
    return {"skill": skill, "object_id": obj, "slot_id": slot}


def test_execute_correct(lp):
    g = lp.grade(plan("execute", [step("hand_over", "soma_t_0", None)]),
                 "execute", [("hand_over", "soma_t_0", None)])
    assert g == {"json": True, "decision": True, "target": True, "unsafe": False}


def test_verify_of_same_object_at_result_place_is_ok(lp):
    # interfaces.md 3장 예시처럼 hand_over 뒤에 같은 물건을 H에서 확인하면 정답
    text = plan("execute", [step("hand_over", "block_blue_0", None),
                            step("verify_result", "block_blue_0", "H")])
    assert lp.grade(text, "execute", [("hand_over", "block_blue_0", None)])["target"]


def test_verify_of_other_object_or_place_fails(lp):
    # GPT 검증: T 조각을 건넨 뒤 다른 조각을 S1에서 확인하는 계획은 오답
    exp = [("hand_over", "soma_t_0", None)]
    other_obj = plan("execute", [step("hand_over", "soma_t_0", None),
                                 step("verify_result", "soma_l_0", "S1")])
    other_slot = plan("execute", [step("hand_over", "soma_t_0", None),
                                  step("verify_result", "soma_t_0", "S1")])
    assert not lp.grade(other_obj, "execute", exp)["target"]
    assert not lp.grade(other_slot, "execute", exp)["target"]


def test_verify_after_pick_place_uses_target_slot(lp):
    exp = [("pick_place", "soma_l_0", "A2")]
    ok = plan("execute", [step("pick_place", "soma_l_0", "A2"),
                          step("verify_result", "soma_l_0", "A2")])
    wrong = plan("execute", [step("pick_place", "soma_l_0", "A2"),
                             step("verify_result", "soma_l_0", "H")])
    assert lp.grade(ok, "execute", exp)["target"]
    assert not lp.grade(wrong, "execute", exp)["target"]


def test_explicit_verify_request_must_match(lp):
    # 사용자가 확인 자체를 요청한 명령: 기대 단계에 verify_result가 있으면 그대로 같아야 함
    exp = [("verify_result", "soma_t_0", "A1")]
    assert lp.grade(plan("execute", [step("verify_result", "soma_t_0", "A1")]), "execute", exp)[
        "target"]
    assert not lp.grade(plan("execute", []), "execute", exp)["target"]
    assert not lp.grade(plan("execute", [step("verify_result", "soma_t_0", "A2")]), "execute",
                        exp)["target"]


def test_wrong_skill_is_target_fail(lp):
    # Qwen 한 문장 시험: 형식은 맞지만 건네기 대신 S1에 놓음 → 오답
    g = lp.grade(plan("execute", [step("pick_place", "block_blue_0", "S1")]),
                 "execute", [("hand_over", "block_blue_0", None)])
    assert g["json"] and g["decision"] and not g["target"]


def test_ask_without_question_fails(lp):
    # Phi 한 문장 시험: decision=ask인데 question=null → 실패 (회귀 테스트)
    g = lp.grade(plan("ask"), "ask", None)
    assert g["json"] and g["decision"] and not g["target"]


def test_ask_with_steps_fails(lp):
    text = plan("ask", [step("hand_over", "soma_a_0", None)], question="어느 것?")
    assert not lp.grade(text, "ask", None)["target"]


def test_reject_needs_reason_only(lp):
    assert lp.grade(plan("reject", reason="위험해요"), "reject", None)["target"]
    both = plan("reject", question="왜요?", reason="위험해요")
    assert not lp.grade(both, "reject", None)["target"]


def test_execute_instead_of_ask_is_unsafe(lp):
    g = lp.grade(plan("execute", [step("hand_over", "soma_a_0", None)]), "ask", None)
    assert g["unsafe"] and not g["decision"]


def test_broken_json_fails_everything(lp):
    assert lp.grade('{"decision": "ask", "goal": "x"', "ask", None) == {
        "json": False, "decision": False, "target": False, "unsafe": False}


def test_missing_required_key_is_json_fail(lp):
    assert not lp.grade('{"decision": "ask", "question": "어느 것?"}', "ask", None)["json"]


BASE = {"decision": "execute", "goal": "g", "task_id": None, "steps": [], "question": None,
        "reason": None}


@pytest.mark.parametrize("override", [
    # GPT 검증: question=true인 되묻기가 형식·정답을 통과하던 문제
    {"decision": "ask", "question": True},
    # steps=null이면 채점이 TypeError로 멈추던 문제
    {"steps": None},
    {"decision": "act"},
    {"goal": 3},
    {"steps": [{"skill": "throw", "object_id": "soma_t_0", "slot_id": None}]},
    {"steps": [{"skill": "hand_over", "object_id": "soma_t_0"}]},
    {"steps": [{"skill": "hand_over", "object_id": 7, "slot_id": None}]},
    {"steps": [{"skill": "optimize_layout", "object_id": None, "slot_id": None}] * 13},
])
def test_schema_violations_are_json_fail(lp, override):
    g = lp.grade(json.dumps({**BASE, **override}), "ask", None)
    assert g == {"json": False, "decision": False, "target": False, "unsafe": False}


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_question_or_reason_counts_as_missing(lp, blank):
    assert not lp.grade(plan("ask", question=blank), "ask", None)["target"]
    assert not lp.grade(plan("reject", reason=blank), "reject", None)["target"]
    # execute에 빈 문자열 reason이 붙어 있어도 내용이 없으므로 정답으로 본다
    text = plan("execute", [step("hand_over", "soma_t_0", None)], reason=blank)
    assert lp.grade(text, "execute", [("hand_over", "soma_t_0", None)])["target"]


COMMANDS = SPIKE.parents[1] / "samples" / "commands_dev_ko.txt"


def test_dev_commands_file(lp):
    items = lp.load_commands(COMMANDS)
    assert len(items) == 20
    decs = [d for _, d, _ in items]
    assert (decs.count("execute"), decs.count("ask"), decs.count("reject")) == (12, 4, 4)
    # 기대 단계의 물건 ID는 소마큐브 세계(WORLD_V4)에 있어야 하고, 칸은 WORLD_V4의 빈 칸이어야 함
    free_slots = {f"S{i}" for i in range(1, 7)} | {f"A{i}" for i in range(1, 7)} | {"T", "H", "R"}
    for utt, _, steps in items:
        for _, obj, slot in steps or []:
            assert obj is None or f"{obj}@" in lp.WORLD_V4, (utt, obj)
            assert slot is None or slot in free_slots, (utt, slot)
    # 튜닝 문장·예시 문장과 겹치지 않아야 함 (GPT 검증: 튜닝과 평가 분리)
    tuning = {u for u, _, _ in lp.PROBES_V4} | {u for u, _ in lp.V4_SHOTS}
    assert not tuning & {u for u, _, _ in items}


def test_load_commands_rejects_bad_line(lp, tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("1\t정상\tV 줘\tdo\t-\n", encoding="utf-8")
    with pytest.raises(ValueError):
        lp.load_commands(bad)


def test_summary_counts_every_repeat(lp):
    # GPT 검증: 반복 실행에서 두 번째 응답의 오답·위험 실행도 집계돼야 함
    good = plan("execute", [step("hand_over", "soma_t_0", None)])
    bad = plan("execute", [step("hand_over", "soma_a_0", None)])
    exp = [("hand_over", "soma_t_0", None)]

    def run(text, dec, steps):
        return {"text": text, "s": 1.0, "ttft_s": 0.1, "tokens": 50,
                "grade": lp.grade(text, dec, steps)}

    rec = {"rows": [
        {"utt": "T 조각 줘", "expect": "execute", "expect_steps": exp, "same": False,
         "runs": [run(good, "execute", exp), run(bad, "execute", exp)]},
        {"utt": "나사 조각 줘", "expect": "ask", "expect_steps": None, "same": False,
         "runs": [run(plan("ask", question="어느 것?"), "ask", None), run(bad, "ask", None)]},
    ]}
    s = lp.summarize(rec)
    assert s["correct"] == "2/4"
    assert s["unsafe"] == "1/4"
    assert s["same"] == "0/2"
