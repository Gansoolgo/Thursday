# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""1 가르치기 — 1-1 티칭 · 1-2 리더암 시범 · 1-3 관절값 저장 기록 · 1-4 모방학습 데이터.

팔은 Mock 입니다 (app/hw 가 생기면 실제 관절값을 읽고 움직임). 실제 팔 움직임은 사람이 확인하며 실행.
"""

from __future__ import annotations

import random
import time

import streamlit as st

from app.ui import logic as lg
from app.ui import widgets as w


def teach() -> None:
    d, c = w.td(), w.cfg("teach")
    st.caption(
        "팔 자세에 이름을 붙여 저장하고, 고치고, 재생합니다. 재생은 지금 Mock 이라 성공/실패가 예시로 나옵니다."
    )
    c1, c2 = st.columns([3, 1])
    name = c1.text_input("새 자세 이름", placeholder="트레이 위", key="pose_name")
    if c2.button("지금 자세 저장", type="primary"):
        if not name.strip():
            st.error("자세 이름을 먼저 입력하세요")
        else:
            d["poses"].append(
                {
                    "n": name.strip(),
                    "j": list(w.joints()),
                    "spd": None,
                    "memo": "",
                    "runs": [],
                    "edits": [],
                }
            )
            st.toast(f'"{name.strip()}" 저장 (지금 팔로워 관절값)')
    w.table(
        [
            {
                "#": i + 1,
                "이름": p["n"],
                "관절 1~6": " ".join(map(str, p["j"])),
                "속도 %": p["spd"] or c["spd"],
                "재생": len(p["runs"]),
                "성공률": lg.pct_ci(sum(r["res"] == "SUCCESS" for r in p["runs"]), len(p["runs"])),
            }
            for i, p in enumerate(d["poses"])
        ]
    )
    if st.button(f"⏭ 1→{len(d['poses'])} 순서 재생 (Mock)"):
        t0, ok = time.time(), True
        for p in d["poses"]:
            res = "SUCCESS" if random.random() > 0.1 else "FAILED"
            p["runs"].append(
                {"t": w.now(), "via": "순서 재생", "res": res, "spd": p["spd"] or c["spd"]}
            )
            st.session_state.jf = list(p["j"])
            if res != "SUCCESS":
                ok = False
                break
        w.add_trial(
            f"순서 재생 1→{len(d['poses'])}",
            "SUCCESS" if ok else "FAILED",
            time.time() - t0 + len(d["poses"]) * 0.7,
        )
        st.toast("재생 끝: " + ("성공" if ok else "실패 (GRASP_FAILED 예시)"))
    st.divider()
    if not d["poses"]:
        return
    names = [f"{i + 1}. {p['n']}" for i, p in enumerate(d["poses"])]
    i = names.index(st.selectbox("자세 고르기 (상세)", names))
    p = d["poses"][i]
    left, right = st.columns(2)
    with left, st.form(f"pose_{i}"):
        nn = st.text_input("이름", p["n"])
        vals = [
            st.number_input(w.JL[k], w.JMIN[k], w.JMAX[k], int(p["j"][k]), 1, key=f"pj_{i}_{k}")
            for k in range(6)
        ]
        follow = st.checkbox(f"작업 설정 속도 따르기 (지금 {c['spd']}%)", value=p["spd"] is None)
        spd = st.slider("이 자세만의 속도 %", 5, 30, p["spd"] or c["spd"])
        memo = st.text_area("메모", p["memo"], placeholder="이 자세에서 조심할 점")
        if st.form_submit_button("변경 저장", type="primary"):
            ch = []
            if nn.strip() and nn.strip() != p["n"]:
                ch.append(f'이름 "{p["n"]}" → "{nn.strip()}"')
                p["n"] = nn.strip()
            nj = w.clamp_joints(vals)
            ch += [
                f"관절 {k + 1}: {a} → {b}"
                for k, (a, b) in enumerate(zip(p["j"], nj, strict=True))
                if a != b
            ]
            p["j"] = nj
            ns = None if follow else spd
            if ns != p["spd"]:
                ch.append(f"속도: {p['spd'] or '작업 설정'} → {ns or '작업 설정'}")
                p["spd"] = ns
            p["memo"] = memo
            p["edits"][:0] = [{"t": w.now(), "m": m} for m in ch]
            st.toast(f"저장됨 ({len(ch)}개 변경)" if ch else "바뀐 값이 없습니다")
    with right:
        if st.button("▶ 이 자세로 가기 (Mock)", key=f"go_{i}"):
            res = "SUCCESS" if random.random() > 0.1 else "FAILED"
            p["runs"].append({"t": w.now(), "via": "단독", "res": res, "spd": p["spd"] or c["spd"]})
            st.session_state.jf = list(p["j"])
            w.add_trial(f'"{p["n"]}" 가기', res, 0.8)
        if st.button("지금 팔 자세로 덮어쓰기", key=f"ow_{i}"):
            old, p["j"] = p["j"], list(w.joints())
            p["edits"].insert(0, {"t": w.now(), "m": f"지금 팔 자세로 덮어씀 ({old} → {p['j']})"})
        if st.button("3D 미리보기", key=f"pv_{i}"):
            st.session_state.preview = list(p["j"])
        st.markdown("**재생 기록**")
        w.table(p["runs"][::-1], "아직 재생한 적이 없습니다.")
        st.markdown("**변경 기록**")
        w.table(p["edits"], "아직 바꾼 적이 없습니다.")
        if st.checkbox("이 자세 지우기", key=f"del_{i}") and st.button(
            "정말 지우기", key=f"dely_{i}"
        ):
            d["poses"].pop(i)
            st.rerun()
    w.cfg_box("teach")
    w.save_bar("teach", "티칭 자세", "팔 자세 저장 · 재생", d["poses"])


def demo() -> None:
    d, ss = w.td(), st.session_state
    st.caption(
        "리더 팔을 손으로 움직이면 팔로워가 따라 하고, 그 움직임을 학습용(LeRobot 형식)으로 녹화합니다. 지금은 Mock."
    )
    if ss.get("rec_t0"):
        sec = time.time() - ss.rec_t0
        st.info(f"녹화 중 · {sec:.1f}초 · 약 {int(sec * 30)} 프레임 (30fps)")
        if st.button("■ 녹화 끝", type="primary"):
            ep = f"ep_{len(d['demos']):03d}"
            d["demos"].append(
                {
                    "t": w.now(),
                    "ep": ep,
                    "sec": round(sec, 1),
                    "frames": int(sec * 30),
                    "use": True,
                    "memo": "",
                }
            )
            ss.rec_t0 = None
            st.rerun()
    elif st.button("● 녹화 시작", type="primary"):
        ss.rec_t0 = time.time()
        st.rerun()
    if d["demos"]:
        edited = st.data_editor(
            [{k: x[k] for k in ("ep", "t", "sec", "frames", "use", "memo")} for x in d["demos"]],
            column_config={"use": st.column_config.CheckboxColumn("학습에 사용"), "memo": "메모"},
            disabled=["ep", "t", "sec", "frames"],
            hide_index=True,
            key="demo_ed",
        )
        for x, e in zip(d["demos"], edited, strict=False):
            x["use"], x["memo"] = e["use"], e["memo"]
        st.caption("실수한 시범은 지우지 말고 '학습에 사용'을 끄세요 — 왜 뺐는지 메모가 남습니다.")
    else:
        st.caption("아직 시범이 없습니다.")
    w.save_bar("demo", "리더암 시범", "리더 팔 시범 녹화", d["demos"])


def jhist() -> None:
    d = w.td()
    st.caption(
        "지금 팔로워 관절값을 한 줄로 남깁니다. 두 줄을 고르면 관절마다 몇 도 달라졌는지 비교합니다."
    )
    c1, c2, c3 = st.columns([3, 1, 1.3])
    memo = c1.text_input("메모", placeholder="블록 위 2cm", key="js_memo")
    who = c2.text_input("누가", "나", key="js_who")
    if c3.button("지금 관절값 저장", type="primary"):
        d["jsnaps"].append({"t": w.now(), "who": who or "나", "j": list(w.joints()), "memo": memo})
    w.table(
        [
            {
                "#": i + 1,
                "시각": x["t"],
                "누가": x["who"],
                "관절 1~6": " ".join(map(str, x["j"])),
                "메모": x["memo"],
            }
            for i, x in enumerate(d["jsnaps"])
        ]
    )
    if len(d["jsnaps"]) >= 2:
        opts = [f"{i + 1}. {x['t']} {x['memo']}" for i, x in enumerate(d["jsnaps"])]
        sel = st.multiselect("비교할 두 줄", opts, max_selections=2)
        if len(sel) == 2:
            a, b = (d["jsnaps"][opts.index(s)]["j"] for s in sel)
            w.table(
                [
                    {
                        "관절": w.JL[k],
                        "A": a[k],
                        "B": b[k],
                        "차이": b[k] - a[k],
                        "5도 넘음": abs(b[k] - a[k]) > 5,
                    }
                    for k in range(6)
                ]
            )
    if d["jsnaps"]:
        k = st.selectbox(
            "한 줄 골라서",
            [f"{i + 1}. {x['t']} {x['memo']}" for i, x in enumerate(d["jsnaps"])],
            key="js_pick",
        )
        x = d["jsnaps"][int(k.split(".")[0]) - 1]
        c1, c2 = st.columns(2)
        if c1.button("3D 미리보기 (실제 팔은 안 움직임)"):
            st.session_state.preview = list(x["j"])
        if c2.button("티칭 자세로 만들기"):
            d["poses"].append(
                {
                    "n": x["memo"] or f"관절값 {x['t']}",
                    "j": list(x["j"]),
                    "spd": None,
                    "memo": "",
                    "runs": [],
                    "edits": [],
                }
            )
            st.toast("1-1 티칭에 추가됨")
    w.save_bar("jhist", "관절값 저장 기록", "관절값 스냅샷 · 비교", d["jsnaps"])


def ds() -> None:
    d = w.td()
    used = [x["ep"] for x in d["demos"] if x["use"]]
    st.caption(
        f"1-2 리더암 시범 중 '학습에 사용' {len(used)}개를 묶어 학습 세트를 만들고, IK 방식과 성공률을 비교합니다 (US-12)."
    )
    c1, c2 = st.columns([3, 1])
    name = c1.text_input("세트 이름", placeholder="블록집기_v1", key="ds_name")
    if c2.button("세트 만들기", type="primary"):
        if not name.strip():
            st.error("세트 이름을 넣으세요")
        elif not used:
            st.error("사용 표시한 시범이 없습니다 (1-2 에서 녹화)")
        else:
            d["dsets"].append(
                {"n": name.strip(), "eps": used, "t": w.now(), "st": "학습 전", "rate": None}
            )
    for i, x in enumerate(d["dsets"]):
        c1, c2 = st.columns([4, 1])
        c1.write(
            f"**{x['n']}** · {', '.join(x['eps'])} · {x['st']}"
            + (f" · ACT 성공률 {x['rate']}% (예시)" if x["rate"] is not None else "")
        )
        if x["st"] == "학습 전" and c2.button("학습 (예시)", key=f"tr_{i}"):
            with st.spinner("학습 중… (실제는 노트북에서 오래 걸림)"):
                time.sleep(1.5)
            x["st"], x["rate"] = "학습 끝", random.randint(60, 90)
            st.rerun()
    runs = [r for p in d["poses"] for r in p["runs"]]
    last = next((x for x in reversed(d["dsets"]) if x["rate"] is not None), None)
    w.table(
        [
            {
                "방식": "IK (티칭 자세 재생)",
                "성공률": lg.pct_ci(sum(r["res"] == "SUCCESS" for r in runs), len(runs)),
                "근거": "1-1 재생 기록",
            },
            {
                "방식": "ACT",
                "성공률": f"{last['rate']}% (예시)" if last else "학습 전",
                "근거": "학습한 세트로 20회 시험",
            },
        ]
    )
    w.save_bar("ds", "모방학습 데이터", "시범 세트 · IK vs ACT", d["dsets"])


PAGES = {"teach": teach, "demo": demo, "jhist": jhist, "ds": ds}
