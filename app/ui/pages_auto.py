# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""99 자율 모드 — 99-1 켜기 · 99-2 세션 기록 (다시 보기).

켜면 시작 전 점검 → 전부 켜짐 → 우리가 행동(지금은 버튼으로 흉내)하면 로봇이
보기 · 듣기 → 생각 → 계획 → 안전 검사 → (질문) → 행동 → 확인 순서로 처리하고, 그 흐름을 보여 줍니다.
켰다 끈 한 번 = 세션 하나 → logs/sessions/<이름>.jsonl 에 저장.
지금 로봇 반응은 Mock (logic.build_act). 진짜 Action Manager(#17)가 생기면 그 사건을 받아 보여 줍니다.
"""

from __future__ import annotations

import json
import random
import re
import time

import streamlit as st

from app.ui import logic as lg
from app.ui import pages_common as pc
from app.ui import widgets as w

NAME_RE = re.compile(r"^[0-9A-Za-z가-힣_\-]{1,40}$")


def _stream_df(stream: list[dict]):
    return [
        {
            "초": s["at"],
            "단계": lg.KIND_KO.get(s["k"], s["k"]),
            "상태": s["f"],
            "내용": s["t"],
            "ms": s["ms"] or "",
        }
        for s in stream
    ]


def _fsm(cur: str) -> str:
    return " · ".join(f"**:blue-background[{f}]**" if f == cur else f for f in lg.FSMS)


def _add(L: dict, step: dict) -> None:
    e = {k: v for k, v in step.items() if k not in ("br", "opts")}
    e["at"] = round(time.time() - L["t0"], 1)
    L["stream"].append(e)
    if L["cur"]:
        L["cur"]["steps"].append(e)


def _finish(L: dict, res: str) -> None:
    c, lat = L["cur"], L["cur"]["lat"]
    total = (
        sum(lat.get(k, 0) for k in ("asr", "plan", "gate")) + lat["motion"]
        if "motion" in lat
        else None
    )
    L["events"].append(
        {
            "t": c["t"],
            "act": c["act"],
            "label": c["label"],
            "res": res,
            "lat": lat,
            "total": total,
            "asked": c["asked"],
            "sec": round(time.time() - c["t0"], 1),
            "steps": c["steps"],
        }
    )
    w.add_trial(
        f"자율: {c['label']}", "SUCCESS" if res == "OK" else res, time.time() - c["t0"], "auto"
    )
    L["cur"], L["fsm"] = None, {"ESTOP": "ESTOP", "HOLD": "HOLD"}.get(res, "IDLE")
    if res != "ESTOP":
        st.session_state.jf = list(w.REST)


def _run(L: dict, ph) -> None:
    """대기열의 단계를 하나씩 처리 (질문이 나오면 멈추고 사람 답을 기다림)."""
    ss, conf = st.session_state, w.cfg("confirm")
    while L["cur"]:
        if ss.get("estop"):
            L["fsm"] = "ESTOP"
            _add(L, {"k": "act", "f": "ESTOP", "t": "비상 정지 — 모든 동작 멈춤", "ms": 0})
            _finish(L, "ESTOP")
            return
        if not L["q"]:
            _finish(L, L["cur"]["res"])
            return
        step = L["q"].pop(0)
        if step["k"] == "ask":
            # 자동 모드: 알리고 바로 실행. 단 "항상 묻기" 질문과 H 근처(설정이 켜져 있으면)는 묻는다 (D-01)
            near_h_ask = step.get("nearH") and conf["near_h"] == "on"
            if L["mode"] == "auto" and not step.get("always") and not near_h_ask:
                _add(
                    L,
                    {
                        "k": "say",
                        "f": "EXECUTE",
                        "t": f'로봇 말: "{step["q"]}" → 자동 모드라 알리고 바로 실행',
                        "ms": 0,
                    },
                )
                continue
            L["fsm"], L["ask"] = "ASK", step
            _add(L, step)
            return
        L["fsm"] = step["f"]
        if step.get("lat"):
            L["cur"]["lat"][step["lat"]] = L["cur"]["lat"].get(step["lat"], 0) + step["ms"]
        if step["k"] == "act" and step.get("j"):
            ss.jf = list(step["j"])
        if step["k"] == "gate" and step.get("bad"):
            L["cur"]["res"] = "REJECT"
        _add(L, step)
        ph.dataframe(_stream_df(L["stream"][-25:]), hide_index=True, width="stretch")
        time.sleep(min(step["ms"] or 0, 1500) / 1000 * 0.25 + 0.15)


def live() -> None:
    ss, d = st.session_state, w.td()
    L = ss.get("live")
    if L and L["task"] != ss.task:
        st.warning(f"다른 작업({L['task']})에서 자율 모드가 켜져 있습니다. 그쪽에서 먼저 끄세요.")
        return
    if not L:
        st.caption(
            "최종본을 실제로 켜 보는 곳입니다. 켜면 시작 전 점검 → 귀 · 눈 · 생각 · 안전 검사 · 팔이 모두 켜지고, 우리가 평소처럼 행동하면 로봇이 "
            "알아채고 생각해서 해결합니다. 켰다 끈 한 번이 세션 하나로 저장됩니다. 음성 원본 · 얼굴 사진은 기본으로 저장하지 않습니다."
        )
        c = w.cfg_box("live", "기본은 확인 모드 · 자동 모드에서도 H 근처는 묻습니다 (3-2 설정)")
        name = st.text_input("세션 이름", placeholder="블록_자율_1차")
        fail = st.checkbox("점검 실패 흉내 (시험용)", key="live_fail")
        if st.button("▶ 자율 모드 켜기", type="primary"):
            if not NAME_RE.match(name.strip()):
                st.error("세션 이름: 한글·영어·숫자·_·- 로 1~40자 (띄어쓰기 대신 _ )")
                return
            if any(s["name"] == name.strip() for s in d["sessions"]):
                st.error("이미 있는 이름입니다")
                return
            st.markdown("**시작 전 점검**")
            checks = pc.run_checks(st.empty(), fail)
            bad = [x["점검"] for x in checks if x["결과"] != "정상"]
            if bad:
                st.error("점검에서 문제가 나와 켜지 않았습니다: " + ", ".join(bad))
                return
            ss.live = {
                "task": ss.task,
                "name": name.strip(),
                "mode": c["mode"],
                "photos": c["photos"] == "on",
                "t0": time.time(),
                "fsm": "IDLE",
                "events": [],
                "stream": [],
                "cur": None,
                "q": [],
                "ask": None,
            }
            _add(
                ss.live,
                {
                    "k": "say",
                    "f": "IDLE",
                    "t": "자율 모드 켜짐 — 귀 · 눈 · 생각 · 안전 검사 · 팔 모두 동작",
                    "ms": 0,
                },
            )
            st.rerun()
        return

    st.markdown(f"### {L['name']} · 켜짐 · {w.OPT_KO[L['mode']]}")
    st.markdown(_fsm(L["fsm"]))
    stats = lg.session_stats(L["events"])
    m = st.columns(5)
    m[0].metric("켜진 시간", f"{time.time() - L['t0']:.0f}초")
    m[1].metric("사건", stats["events"])
    m[2].metric("해결", stats["ok"])
    m[3].metric("사람이 답한 질문", stats["asked"])
    m[4].metric(
        "말 끝 → 움직임 (중앙값)", f"{stats['median'] / 1000:.1f}초" if stats["median"] else "-"
    )
    ph = st.empty()
    if L["cur"] and not L["ask"]:  # 다시 그려지느라 중간에 멈춘 처리 이어서 하기
        _run(L, ph)
    if L["ask"]:
        st.warning(L["ask"]["t"])
        opts = L["ask"].get("opts") or [["응", "yes"], ["아니", "no"]]
        for col, (label, key) in zip(st.columns(len(opts)), opts, strict=True):
            if col.button(
                label, key=f"la_{key}", type="primary" if key == opts[0][1] else "secondary"
            ):
                step, L["ask"] = L["ask"], None
                L["cur"]["asked"] += 1
                _add(L, {"k": "hear", "f": "OBSERVE", "t": f'사람: "{label}"', "ms": 0})
                if step.get("br") and key in step["br"]:
                    L["q"] = step["br"][key] + L["q"]
                elif key == "no":
                    L["q"], L["cur"]["res"] = (
                        [
                            {
                                "k": "say",
                                "f": "IDLE",
                                "t": '로봇 말: "알겠어요, 안 할게요."',
                                "ms": 200,
                            }
                        ],
                        "CANCEL",
                    )
                _run(L, ph)
                st.rerun()
    st.markdown("**우리 행동** — 시안이라 버튼으로 흉내 · 실제로는 카메라 · 마이크가 알아챔")
    acts = lg.acts_for(ss.task)
    cols = st.columns(3)
    for i, (k, label) in enumerate(acts):
        if cols[i % 3].button(
            label, key=f"act_{k}", disabled=bool(L["cur"]), width="stretch"
        ):
            b = lg.build_act(k, ss.task, random.Random())
            L["cur"] = {
                "act": k,
                "label": b["label"],
                "t": w.now(),
                "steps": [],
                "lat": {},
                "res": b["res"],
                "asked": 0,
                "t0": time.time(),
            }
            L["q"] = list(b["steps"])
            _run(L, ph)
            st.rerun()
    ph.dataframe(_stream_df(L["stream"][-25:]), hide_index=True, width="stretch")
    if st.button("■ 끄고 저장", type="primary"):
        if L["cur"]:
            L["q"], L["ask"] = [], None
            _finish(L, "ABORTED")
        s = {
            "name": L["name"],
            "t": time.strftime("%H:%M", time.localtime(L["t0"])),
            "mode": L["mode"],
            "photos": L["photos"],
            "sec": round(time.time() - L["t0"], 1),
            "events": L["events"],
            "stream": L["stream"],
            "stats": lg.session_stats(L["events"]),
        }
        path = w.LOG_DIR / "sessions" / f"{L['name']}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for e in L["events"]:
                f.write(
                    json.dumps(
                        {
                            "session": L["name"],
                            "task_id": ss.task,
                            **{k: v for k, v in e.items() if k != "steps"},
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        d["sessions"].append(s)
        ss.live, ss.estop = None, False
        ss.sess_pick = len(d["sessions"]) - 1
        ss.item = "sessions"
        st.rerun()


def sessions() -> None:
    ss, d = st.session_state, w.td()
    if not d["sessions"]:
        st.caption("아직 세션이 없습니다. 99-1 에서 켜 보세요.")
        return
    w.table(
        [
            {
                "이름": s["name"],
                "시각": s["t"],
                "방식": w.OPT_KO[s["mode"]],
                "길이 초": s["sec"],
                "사건": s["stats"]["events"],
                "해결": s["stats"]["ok"],
                "말→움직임 중앙값 초": round(s["stats"]["median"] / 1000, 1)
                if s["stats"]["median"]
                else "-",
            }
            for s in d["sessions"]
        ]
    )
    names = [s["name"] for s in d["sessions"]]
    i = names.index(
        st.selectbox("세션 고르기", names, index=min(ss.get("sess_pick", 0), len(names) - 1))
    )
    s = d["sessions"][i]
    st.markdown(f"### {s['name']}")
    w.table(
        [
            {
                "시각": e["t"],
                "사건": e["label"],
                "결과": e["res"],
                "음성 인식": e["lat"].get("asr", "-"),
                "계획": e["lat"].get("plan", "-"),
                "검사": e["lat"].get("gate", "-"),
                "움직임 시작": e["lat"].get("motion", "-"),
                "합계 초": round(e["total"] / 1000, 1) if e["total"] else "-",
                "질문": e["asked"],
            }
            for e in s["events"]
        ],
        "사건 없이 끈 세션입니다.",
    )
    st.caption(
        "단위 ms · REJECT = 안전 검사가 막음(맞게 막은 것) · HOLD = 멈추고 기다림 · CANCEL = 사람이 '아니' · 음성 원본은 저장 안 함"
    )
    ph_f, ph = st.empty(), st.empty()
    if st.button("▶ 다시 보기"):
        shown = []
        for step in s["stream"]:
            shown.append(step)
            ph_f.markdown(_fsm(step["f"]))
            if step["k"] == "act" and step.get("j"):
                ss.jf = list(step["j"])
            ph.dataframe(_stream_df(shown[-25:]), hide_index=True, width="stretch")
            time.sleep(min(step["ms"] or 0, 1500) / 1000 * 0.2 + 0.12)
    else:
        ph.dataframe(_stream_df(s["stream"]), hide_index=True, width="stretch")
    w.save_bar(
        "session",
        "자율 모드 세션",
        "말 → 해결까지 사건 · 걸린 시간",
        {k: v for k, v in s.items() if k != "stream"},
        rows=[
            ("사건", str(s["stats"]["events"])),
            ("해결", str(s["stats"]["ok"])),
            (
                "말→움직임 중앙값(ms)",
                str(s["stats"]["median"]) if s["stats"]["median"] else "(확인 필요)",
            ),
        ],
    )
