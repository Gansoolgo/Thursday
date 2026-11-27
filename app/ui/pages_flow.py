# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""4 작업 진행 — 4-1 작업 설명서 · 4-2 단계 추정 · 순서 이탈 · 4-3 정리 시뮬레이션.

작업 설명서는 tasks/<id>.yaml 이 최종 위치지만, v0 은 팀 합의 전이라 logs/hanbang/tasks/ 에 저장합니다.
"""

from __future__ import annotations

import time

import streamlit as st

from app.ui import logic as lg
from app.ui import slots as sl
from app.ui import widgets as w

OBJECTS = [
    "block_tray",
    "block_blue",
    "block_yellow",
    "block_red",
    "block_green",
    "block_orange",
    "block_white",
    "resistor_case",
    "cloth",
    "test_stick",
]


def manual_yaml(task: str, m: dict) -> str:
    import yaml

    data = {"task_id": task, "name": m["name"], "required_objects": m["objects"]}
    if m["setup"] and "→" in m["setup"]:
        a, b = (x.strip() for x in m["setup"].split("→", 1))
        data["setup"] = {"move": a, "to": b}
    if m["order"]:
        data["order"] = [
            {"slot": f"A{i + 1}", "object": f"block_{c}"} for i, c in enumerate(m["order"])
        ]
    else:
        data["steps"] = m["steps"]
    data["notes"] = m["notes"]
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def manual() -> None:
    d, ss = w.td(), st.session_state
    m = d["manual"]
    ss.setdefault("mf_open", {}).setdefault(ss.task, time.time())
    st.caption(
        "새 작업은 코드를 고치지 않고 이 설명서만 쓰면 됩니다 (가설 H1). 저장할 때 이 화면을 연 뒤 걸린 시간과 엔진 코드 수정 줄 수(0줄)를 같이 남깁니다."
    )
    left, right = st.columns(2)
    with left:
        m["name"] = st.text_input("이름", m["name"], key=f"mf_name_{ss.task}")
        m["objects"] = st.multiselect(
            "필요한 물건",
            OBJECTS,
            default=[o for o in m["objects"] if o in OBJECTS],
            key=f"mf_obj_{ss.task}",
        )
        use_order = st.toggle(
            "블록 순서 방식 (A1 = 사람에게 가장 가까운 칸)",
            value=bool(m["order"]),
            key=f"mf_mode_{ss.task}",
        )
        if use_order:
            base = m["order"] or list(lg.COLORS)
            cols = st.columns(6)
            m["order"] = [
                cols[i].selectbox(
                    f"A{i + 1}",
                    list(lg.COLORS),
                    index=list(lg.COLORS).index(base[i]),
                    format_func=lg.COLORS.get,
                    key=f"mf_o{i}_{ss.task}",
                )
                for i in range(6)
            ]
        else:
            m["order"] = []
            m["steps"] = [
                s.strip()
                for s in st.text_area(
                    "단계 (한 줄에 하나)", "\n".join(m["steps"]), key=f"mf_steps_{ss.task}"
                ).splitlines()
                if s.strip()
            ]
        m["setup"] = st.text_input(
            "시작 동작", m["setup"], placeholder="block_tray → T", key=f"mf_setup_{ss.task}"
        )
        m["notes"] = st.text_area("메모", m["notes"], key=f"mf_notes_{ss.task}")
    with right:
        y = manual_yaml(ss.task, m)
        st.code(y, language="yaml")
        el = int(time.time() - ss.mf_open[ss.task])
        m1, m2, m3 = st.columns(3)
        m1.metric("이 화면 연 뒤", f"{el // 60}분 {el % 60}초")
        m2.metric("엔진 코드 수정", "0줄")
        m3.metric("저장한 버전", len(m["ver"]))
        if st.button("설명서 저장", type="primary"):
            path = w.HANBANG_DIR / "tasks" / f"{ss.task}.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(y, encoding="utf-8")
            m["ver"].append({"t": w.now(), "작성 초": el, "버전": len(m["ver"]) + 1})
            ss.mf_open[ss.task] = time.time()
            d["prog"] = None
            st.success(f"저장됨 → {path.relative_to(w.ROOT)} (팀 합의 후 tasks/ 로)")
        w.table(m["ver"][::-1], "아직 저장 안 함")
    w.save_bar(
        "manual",
        "작업 설명서",
        "H1 새 작업 추가 시간",
        m,
        rows=[
            ("마지막 작성 시간(초)", str(m["ver"][-1]["작성 초"]) if m["ver"] else "(확인 필요)"),
            ("엔진 코드 수정 줄", "0"),
        ],
    )


def progress() -> None:
    d = w.td()
    if d["prog"] is None:
        d["prog"] = lg.new_progress(d["manual"]["order"] or list(lg.COLORS))
    p = d["prog"]
    st.caption(
        "조립 줄에 놓인 색을 작업 설명서 순서와 **규칙으로 비교**합니다 (AI 아님). 다르면 묻고, 같으면 말없이 다음 블록을 준비합니다. "
        "색 버튼 = '사람이 그 색을 다음 칸에 놓음'."
    )
    cols = st.columns(6)
    for i in range(6):
        pl = p["placed"][i] if i < len(p["placed"]) else None
        exp = pl["exp"] if pl else p["order"][i]
        mark = ("⚠ " if pl and pl["dev"] else "■ ") + lg.COLORS[pl["c"]] if pl else "□ 비어 있음"
        cols[i].markdown(
            f"**A{i + 1}**  \n{mark}  \n<small>기대 {lg.COLORS[exp]}</small>",
            unsafe_allow_html=True,
        )
    n = len(p["placed"])
    if p["ask"]:
        a = p["ask"]
        st.warning(
            f'로봇: "{lg.COLORS[a["exp"]]} 차례인데 {lg.COLORS[a["c"]]}을(를) 놓으셨어요. 이대로 갈까요?"'
        )
        c1, c2 = st.columns(2)
        if c1.button("이대로", type="primary"):
            lg.answer(p, "keep")
            st.rerun()
        if c2.button(f"실수 — {lg.COLORS[a['exp']]} 줘"):
            lg.answer(p, "fix")
            st.rerun()
    elif n >= 6:
        st.success('로봇: "다 끝났어요. 정리할까요?"')
    else:
        st.write(f"A{n + 1} 에 놓기:")
        for col, (c, name) in zip(st.columns(6), lg.COLORS.items(), strict=True):
            if col.button(name, key=f"pl_{c}"):
                lg.place(p, c)
                st.rerun()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("로봇이 추정한 단계", f"{min(n, 6)} / 6")
    m2.metric("다음 준비", "-" if n >= 6 else lg.COLORS[p["order"][n]])
    m3.metric("순서 이탈 감지", f"{sum(e['k'] == '이탈' for e in p['events'])}번")
    m4.metric("단계 추정 정확도", lg.pct_ci(sum(p["truth"]), len(p["truth"])))
    c1, c2, c3 = st.columns(3)
    if c1.button("✓ 로봇 추정이 맞음 (정답)"):
        p["truth"].append(True)
    if c2.button("✗ 틀림 (정답)"):
        p["truth"].append(False)
    if c3.button("처음부터"):
        d["prog"] = lg.new_progress(d["manual"]["order"] or list(lg.COLORS))
        d["prog"]["events"] = p["events"] + [{"k": "질문", "m": "처음부터 다시"}]
        d["prog"]["truth"] = p["truth"]
        st.rerun()
    w.table(p["events"][::-1][:12], "색 버튼을 눌러 블록을 놓아 보세요.")
    w.cfg_box("progress")
    w.save_bar(
        "progress",
        "단계 추정 · 순서 이탈",
        "H4 · D-14",
        p,
        rows=[
            ("단계 추정 정확도", lg.pct_ci(sum(p["truth"]), len(p["truth"]))),
            ("순서 이탈 감지", str(sum(e["k"] == "이탈" for e in p["events"]))),
        ],
    )


def layout() -> None:
    d, c, ss = w.td(), w.cfg("layout"), st.session_state
    slots = ss.get("slots") or sl.default_slots()
    robots = ss.get("robots") or sl.ROBOTS
    st.caption(
        "로봇 없이 계산합니다. 0-1 작업대 지도의 칸 좌표와 5-1 사용 기록(많이 쓴 물건)으로 정리 방법 4가지를 비교합니다. "
        "값 = 사용 횟수 × 가장 가까운 팔까지 거리의 합 (작을수록 꺼내기 쉬움). 시안은 욕심쟁이 배정, 실제는 헝가리안(#16)."
    )
    counts: dict[str, int] = {}
    for u in d["usage"]:
        if u["사건"] != "returned":
            counts[u["물건"]] = counts.get(u["물건"], 0) + 1
    objs = [
        (o, "big" if o in ("block_tray", "resistor_case", "cloth") else "small", counts.get(o, 1))
        for o in d["manual"]["objects"] or OBJECTS[:4]
    ]
    if st.button("4가지 방법 비교", type="primary"):
        res = lg.compare_layouts(objs, slots, robots, alpha=c["alpha"], beta=c["beta"])
        d["layout_runs"].append(
            {
                "t": w.now(),
                "alpha": c["alpha"],
                "beta": c["beta"],
                **{k: v["cost"] for k, v in res.items()},
                "fused_assign": res["fused"]["assign"],
            }
        )
    if d["layout_runs"]:
        r = d["layout_runs"][-1]
        names = {
            "fixed": "① 고정 자리",
            "usage": "② 사용 기록만",
            "space": "③ 공간만",
            "fused": "④ 합침 (D-02)",
        }
        st.bar_chart({names[k]: r[k] for k in names}, horizontal=True)
        if r["fixed"]:
            st.write(
                f"고정 자리보다 **{round((1 - r['fused'] / r['fixed']) * 100)}%** 줄어듦 · 합침 배정: {r['fused_assign']}"
            )
    st.caption("물건 · 사용 횟수: " + ", ".join(f"{o}×{n}" for o, _, n in objs))
    w.table([{k: v for k, v in x.items() if k != "fused_assign"} for x in d["layout_runs"][::-1]])
    w.cfg_box("layout")
    w.save_bar("layout", "정리 시뮬레이션", "H3 정리 방법 비교", d["layout_runs"])


PAGES = {"manual": manual, "progress": progress, "layout": layout}
