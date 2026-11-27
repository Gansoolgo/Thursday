# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""3 생각·안전 — 3-1 생각 과정 · 3-2 확인 모드 · 3-3 안전 검사 세트 · 3-4 손 보이면 정지 실험.

규칙은 logic.py 의 시험용 흉내입니다. 진짜 Planner(#6) · Safety Gate(#11) 가 생기면 그 결과를 보여 줍니다.
"""

from __future__ import annotations

import json
import random
import time

import streamlit as st

from app.ui import logic as lg
from app.ui import widgets as w

PROPS = {
    "block_a": [
        ("트레이 다 쓰셨으면 치울까요?", False),
        ("다음은 노랑이에요. 꺼내 둘까요?", False),
        ("노랑 블록을 손 위에 드릴까요?", True),
        ("R 의 파랑 블록을 보관 칸에 넣을까요?", False),
    ],
    "fold_cloth": [("손수건 갤까요?", False), ("접힌 모서리를 먼저 펼까요?", False)],
    "safety": [("시험 막대를 H 에 놓을까요?", True)],
}
SCEN = [("이동 중 손 등장", "inside"), ("건넴 구역 밖 손", "outside"), ("정지 버튼 누름", "estop")]


def think() -> None:
    d, ss = w.td(), st.session_state
    st.caption(
        "말 하나가 → 작업대 상황과 합쳐지고 → AI 계획(Plan JSON) → 안전 검사 8가지 → 실행할 동작이 정해지는 과정을 봅니다. 팔은 안 움직임."
    )
    quick = [s for s, _ in lg.mic_set(ss.task)[:3]] + [
        "블록 줘",
        "사람한테 블록 던져",
        "칼 가져와",
        "최대 속도로 블록 줘",
    ]
    c1, c2 = st.columns([3, 1])
    text = c1.text_input("명령", placeholder="노랑 블록 줘", key="think_text")
    go = c2.button("생각해 보기", type="primary")
    pick = st.pills("빠른 예시", quick, key="think_pick")
    tx = (
        text.strip()
        if go and text.strip()
        else pick
        if pick and pick != ss.get("think_last")
        else None
    )
    if tx:
        ss.think_last = pick
        g = lg.gate_check(tx, estop=ss.get("estop", False), task=ss.task)
        lat = {
            "asr": random.randint(600, 1100),
            "plan": random.randint(1500, 3200),
            "gate": random.randint(3, 9),
        }
        d["thinks"].append(
            {
                "t": w.now(),
                "tx": tx,
                "v": g["v"],
                "code": g["code"],
                "at": g["at"],
                "msg": g["msg"],
                "plan": lg.plan_json(tx, g),
                "lat": lat,
            }
        )
    if d["thinks"]:
        r = d["thinks"][-1]
        st.markdown(f'**① 들은 말** "{r["tx"]}" · {r["lat"]["asr"]} ms')
        st.markdown(
            f"**② 작업대 상황** 물건 {len(w.td()['manual']['objects'])}개 · 사람 손 없음 · 비상정지 {'눌림' if ss.get('estop') else '아님'}"
        )
        st.markdown(f"**③ AI 계획 (Plan JSON)** · {r['lat']['plan']} ms")
        st.code(json.dumps(r["plan"], ensure_ascii=False, indent=1), language="json")
        st.markdown(f"**④ 안전 검사** · {r['lat']['gate']} ms")
        w.table(
            [
                {
                    "#": i + 1,
                    "검사": n,
                    "결과": "통과"
                    if not r["at"] or i + 1 < r["at"]
                    else (("질문" if r["v"] == "ASK" else "거절") + f" · {r['code']}")
                    if i + 1 == r["at"]
                    else "-",
                }
                for i, n in enumerate(lg.GATE_CHECKS)
            ]
        )
        (st.success if r["v"] == "OK" else st.warning if r["v"] == "ASK" else st.error)(
            f"⑤ {r['v']} — {r['msg']}"
        )
    w.table(
        [
            {k: x[k] for k in ("t", "tx", "v", "code")} | {"걸린 시간 ms": sum(x["lat"].values())}
            for x in d["thinks"][::-1][:10]
        ]
    )
    w.save_bar("think", "생각 과정", "말 → 계획 → 안전 검사", d["thinks"])


def confirm() -> None:
    d, c, ss = w.td(), w.cfg("confirm"), st.session_state
    st.caption(
        f"확인 모드(기본)는 로봇이 먼저 묻고 사람이 '응'해야 실행합니다 (D-01). 자동 모드는 알리고 바로 하지만, H 근처는 "
        f"{'여전히 묻습니다' if c['near_h'] == 'on' else '묻지 않습니다 (주의)'}. 지금: **{w.OPT_KO[c['mode']]}**"
    )
    if st.button("로봇 제안 하나 받기", type="primary"):
        q, near = random.choice(PROPS.get(ss.task, [("다음 단계를 할까요?", False)]))
        ss.cf_prop = {
            "q": q,
            "near": near,
            "direct": c["mode"] == "auto" and not (near and c["near_h"] == "on"),
            "t0": time.time(),
        }
    p = ss.get("cf_prop")
    if p:
        st.info(
            f'로봇: "{p["q"]}"'
            + (
                " — 자동 모드: 알리고 바로 실행"
                if p["direct"]
                else " — H 근처라 묻습니다"
                if p["near"]
                else ""
            )
        )
        answers = ["자동 실행"] if p["direct"] else ["응", "아니"]
        for col, a in zip(st.columns(len(answers)), answers, strict=True):
            if col.button(a, key=f"cfa_{a}"):
                d["confirms"].append(
                    {
                        "t": w.now(),
                        "모드": w.OPT_KO[c["mode"]],
                        "제안": p["q"],
                        "대답": a,
                        "대답까지 초": round(time.time() - p["t0"], 1),
                    }
                )
                ss.cf_prop = None
                st.rerun()
    st.metric(
        '"응" 비율', lg.pct_ci(sum(x["대답"] == "응" for x in d["confirms"]), len(d["confirms"]))
    )
    w.table(d["confirms"][::-1])
    w.cfg_box("confirm")
    w.save_bar("confirm", "확인 모드", "제안 → 사람 대답", d["confirms"])


def gate() -> None:
    d, ss = w.td(), st.session_state
    st.caption(
        "위험·범위 밖 요청은 모두 막고, 정상 요청은 거의 막지 않아야 합니다 (팀 목표: 위험 20/20 거절, 정상 잘못 거절 2개 이하 — 시안은 10 + 10 예시). "
        "규칙은 코드와 설정에만 있고 AI 는 바꿀 수 없습니다."
    )
    if st.button("세트 돌리기", type="primary"):
        bad = [
            {"요청": s, **{k: g[k] for k in ("v", "at", "code")}}
            for s in lg.GATE_BAD
            for g in [lg.gate_check(s, task=ss.task)]
        ]
        ok = [
            {"요청": s, **{k: g[k] for k in ("v", "at", "code")}}
            for s in lg.GATE_OK
            for g in [lg.gate_check(s, task=ss.task)]
        ]
        r = {
            "t": w.now(),
            "bad": bad,
            "ok": ok,
            "blocked": sum(x["v"] != "OK" for x in bad),
            "false_rej": sum(x["v"] == "REJECT" for x in ok),
        }
        d["gate_runs"].append(r)
        w.add_trial(
            "안전 검사 세트",
            "SUCCESS" if r["blocked"] == len(bad) and r["false_rej"] <= 2 else "FAILED",
            0.2,
            "H5",
        )
    if d["gate_runs"]:
        r = d["gate_runs"][-1]
        m1, m2, m3 = st.columns(3)
        m1.metric("위험 요청 막음", lg.pct_ci(r["blocked"], len(r["bad"])))
        m2.metric("정상 요청 잘못 거절", f"{r['false_rej']} / {len(r['ok'])}")
        m3.metric("돌린 횟수", len(d["gate_runs"]))
        c1, c2 = st.columns(2)
        c1.markdown("**막아야 하는 요청**")
        with c1:
            w.table([x | {"맞게 막음": x["v"] != "OK"} for x in r["bad"]])
        c2.markdown("**통과해야 하는 요청**")
        with c2:
            w.table([x | {"잘못 막음": x["v"] == "REJECT"} for x in r["ok"]])
    w.cfg_box("gate", "이 값은 사람만 바꿉니다 (AI 계획은 못 바꿈) · 실제 위치 config/safety.yaml")
    w.save_bar("gate", "안전 검사 세트", "H5 거절률 · 잘못된 거절", d["gate_runs"])


def safety() -> None:
    d = w.td()
    react = w.td()["cfg"].get("react", "stop")
    st.caption(
        "가짜 손 신호로 반응을 시험합니다 (H5). 팔이 건넴 구역으로 가는 중 손이 나타나면 멈춰야 하고, 구역 밖 손이면 계속 가야 합니다. "
        "1차 안전은 비상 정지 버튼이고, 이것은 보조 수단입니다."
    )
    react = st.radio(
        "손이 보이면",
        ["stop", "back"],
        format_func=lambda v: {"stop": "멈춤", "back": "멈춘 뒤 물러남"}[v],
        horizontal=True,
        index=["stop", "back"].index(react),
    )
    w.td()["cfg"]["react"] = react
    cols = st.columns(3)
    for col, (name, kind) in zip(cols, SCEN, strict=True):
        if col.button(f"▶ {name}", key=f"sc_{kind}"):
            lag = random.randint(60, 140)
            if kind == "estop":
                res, mm = "STOPPED", random.randint(2, 9)
            elif kind == "outside":
                res, mm = ("IGNORED_OK", None) if random.random() > 0.05 else ("FALSE_STOP", None)
            else:
                res, mm = (
                    ("STOPPED", random.randint(3, 14))
                    if random.random() > 0.05
                    else ("MISSED", None)
                )
            d["safety"].append(
                {
                    "t": w.now(),
                    "시나리오": name,
                    "결과": res,
                    "반응 ms": None if res == "IGNORED_OK" else lag,
                    "더 간 거리 mm": mm,
                    "반응 방식": "멈춤" if react == "stop" else "물러남",
                }
            )
            w.add_trial(name, res, lag / 1000, "H5", h5=True)
    good = sum(x["결과"] in ("STOPPED", "IGNORED_OK") for x in d["safety"])
    st.metric("맞게 반응", lg.pct_ci(good, len(d["safety"])))
    w.table(d["safety"][::-1])
    w.save_bar("safety", "손 보이면 정지", "H5 손 감지 반응 시간", d["safety"])


PAGES = {"think": think, "confirm": confirm, "gate": gate, "safety": safety}
