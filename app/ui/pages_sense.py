# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""2 듣기·보기 시험 — 2-1 마이크·음성 · 2-2 물체 인식 · 2-3 카메라 좌표 · 2-4 손 위 전달 / 손수건 상태.

팔은 움직이지 않습니다. 인식 · 손 위치 값은 Mock (모델 · 카메라가 연결되면 그 결과로 바꿈).
"""

from __future__ import annotations

import random

import streamlit as st

from app.ui import logic as lg
from app.ui import slots as sl
from app.ui import widgets as w

VOBJ = {
    "block_a": [
        "block_blue",
        "block_yellow",
        "block_red",
        "block_green",
        "block_orange",
        "block_white",
        "block_tray",
    ],
    "fold_cloth": ["cloth"],
    "safety": ["test_stick"],
}


def _mic_add(
    text: str, src: str, conf: int | None, ms: int | None, expect: str | None = None
) -> dict:
    c, p = w.cfg("mic"), lg.parse_cmd(text, st.session_state.task)
    exp = expect or dict(lg.mic_set(st.session_state.task)).get(text)
    low = conf is not None and conf < c["min_conf"]
    r = {
        "t": w.now(),
        "heard": text,
        "src": src,
        "conf": conf,
        "ms": ms,
        "cmd": p["cmd"] if p else None,
        "low": low,
        "expect": exp,
        "ok": None if exp is None else bool(p and p["cmd"] == exp and not low),
    }
    w.td()["mic"].append(r)
    return r


def mic() -> None:
    d, c = w.td(), w.cfg("mic")
    st.caption(
        "말하면 → 알아들은 글자 → 실행할 명령으로 바뀌는지만 봅니다. **팔은 움직이지 않습니다.** "
        "저장은 팀 규칙대로 글자만 (음성 원본은 남기지 않음)."
    )
    audio = st.audio_input("마이크로 말하기")
    if audio is not None:
        st.info(
            "녹음은 받았어요. 글자로 바꾸는 오프라인 음성 인식(Whisper · OpenVINO)은 #29 결과로 연결합니다. "
            "그때까지는 아래에 들은 문장을 입력해 시험하세요. (녹음 파일은 저장하지 않음)"
        )
    c1, c2, c3 = st.columns([3, 1, 1.6])
    text = c1.text_input("말 대신 입력", placeholder="노랑 블록 줘", key="mic_text")
    if c2.button("입력으로 시험", type="primary") and text.strip():
        _mic_add(text.strip(), "입력", random.randint(70, 99), random.randint(500, 1000))
    if c3.button(f"세트 시험 ({len(lg.mic_set(st.session_state.task))}문장 · 예시)"):
        for s, exp in lg.mic_set(st.session_state.task):
            heard = s
            if random.random() < 0.1:
                heard = s.replace("노랑", "").replace("파랑", "").replace("초록", "").strip() or s
            _mic_add(
                heard, "세트 (예시)", random.randint(62, 99), random.randint(520, 1100), expect=exp
            )
    if d["mic"]:
        r = d["mic"][-1]
        verdict = (
            f"확신 {c['min_conf']}% 아래 → 되묻기"
            if r["low"]
            else "실행 가능"
            if r["cmd"]
            else '명령 아님 → "다시 말씀해 주세요"'
        )
        st.success(
            f'들은 말 "{r["heard"]}" → 명령 `{r["cmd"] or "알 수 없음"}` · {verdict}'
            + (f" · 정답 `{r['expect']}` {'✓' if r['ok'] else '✗'}" if r["expect"] else "")
        )
    judged = [x for x in d["mic"] if x["ok"] is not None]
    ms = [x["ms"] for x in d["mic"] if x["ms"]]
    m1, m2, m3 = st.columns(3)
    m1.metric("시험한 문장", len(d["mic"]))
    m2.metric("정답 맞춤 (95% 범위)", lg.pct_ci(sum(x["ok"] for x in judged), len(judged)))
    m3.metric("평균 걸린 시간", f"{sum(ms) / len(ms):.0f} ms" if ms else "-")
    w.table(d["mic"][::-1][:15])
    with st.expander("시험 문장 세트"):
        st.write(lg.mic_set(st.session_state.task))
    w.cfg_box("mic")
    w.save_bar(
        "mic",
        "마이크·음성",
        "음성 → 글자 → 명령 정확도",
        d["mic"],
        rows=[("음성 명령 정확도", lg.pct_ci(sum(x["ok"] for x in judged), len(judged)))],
    )


def vision() -> None:
    d, c = w.td(), w.cfg("vision")
    st.caption(
        "위 카메라(HP60C ①) 한 장으로 물건 이름 · 확신 % · 위치(mm) · 칸을 봅니다. 'O/X' 칸에 정답을 표시하면 정답률이 계산됩니다. "
        "실제 모델은 Geti → OpenVINO (#7). 지금은 Mock 결과."
    )
    if st.button("인식 1회", type="primary"):
        slots = st.session_state.get("slots") or sl.default_slots()
        dets = []
        for i, o in enumerate(VOBJ.get(st.session_state.task, ["object_1"])):
            s = next((x for x in slots if x.home == o), slots[i % len(slots)])
            conf = random.randint(48, 99)
            dets.append(
                {
                    "물건": o,
                    "확신 %": conf,
                    "x": s.center_mm[0] + random.randint(-4, 4),
                    "y": s.center_mm[1] + random.randint(-4, 4),
                    "z": random.randint(0, 6),
                    "칸": s.id,
                    "기준 아래": conf < c["min_conf"],
                    "정답": None,
                }
            )
        d["vis"].append({"t": w.now(), "ms": random.randint(28, 60), "dets": dets})
    if d["vis"]:
        r = d["vis"][-1]
        st.markdown(f"**{r['t']} · {r['ms']} ms**")
        edited = st.data_editor(
            r["dets"],
            column_config={"정답": st.column_config.CheckboxColumn("정답 (맞으면 체크)")},
            disabled=[k for k in r["dets"][0] if k != "정답"],
            hide_index=True,
            key=f"vis_{len(d['vis'])}",
        )
        for x, e in zip(r["dets"], edited, strict=False):
            x["정답"] = e["정답"]
    marked = [x for v in d["vis"] for x in v["dets"] if x["정답"] is not None]
    m1, m2 = st.columns(2)
    m1.metric("인식 횟수", len(d["vis"]))
    m2.metric("정답률 (체크한 것)", lg.pct_ci(sum(bool(x["정답"]) for x in marked), len(marked)))
    w.cfg_box("vision", "손이 칸을 가리면 물건이 사라진 것처럼 보여서, 몇 장 연속 같을 때만 인정")
    w.save_bar("vision", "물체 인식", "인식 이름 · 확신 · 위치 정답률", d["vis"])


def coord() -> None:
    d = w.td()
    st.caption(
        "카메라 화면의 점(픽셀 u, v)을 작업대 좌표(mm)로 바꿔 저장합니다. 지금 변환은 예시 계산 — 실제는 0-3 카메라 보정(#9) 결과를 씁니다."
    )
    c1, c2, c3, c4 = st.columns(4)
    u = c1.number_input("u (픽셀)", 0, 639, 320)
    v = c2.number_input("v (픽셀)", 0, 479, 240)
    label = c3.text_input("이름", placeholder="트레이 모서리")
    if c4.button("저장", type="primary"):
        x, y = round(450 - v / 480 * 450), round((u - 320) / 320 * 300)
        d["coords"].append(
            {
                "t": w.now(),
                "이름": label or f"점 {len(d['coords']) + 1}",
                "u": u,
                "v": v,
                "x": x,
                "y": y,
                "z": 0,
                "깊이 mm": random.randint(520, 700),
            }
        )
    w.table(d["coords"][::-1])
    if d["coords"] and st.button("마지막 점으로 티칭 자세 만들기 (IK 예시)"):
        p = d["coords"][-1]
        d["poses"].append(
            {
                "n": f"{p['이름']} 위",
                "j": w.clamp_joints([random.randint(-40, 40), -20, 50, 50, 0, 50]),
                "spd": None,
                "memo": f"좌표 ({p['x']}, {p['y']})",
                "runs": [],
                "edits": [],
            }
        )
        st.toast("1-1 티칭에 추가됨")
    w.save_bar("coord", "카메라 좌표", "픽셀 → 작업대 mm", d["coords"])


def hand() -> None:
    d, c = w.td(), w.cfg("hand")
    st.caption(
        f"D-08: 건넬 때 {c['wait']}초 안에 건넴 구역에 손이 멈춰 있으면 손 위 {c['above']}cm 에서 놓고, 아니면 칸 H 에 놓습니다. "
        "움직이는 손은 따라가지 않고 멈춥니다. 아래 버튼 = 상황 만들기(정답)."
    )
    cols = st.columns(4)
    for col, (k, label) in zip(cols, lg.HAND_SIT.items(), strict=True):
        if col.button(label, key=f"hs_{k}"):
            right = lg.hand_choice(k)
            got = (
                right if random.random() > 0.1 else ("slot_H" if right == "on_hand" else "on_hand")
            )
            d["hand"].append(
                {
                    "t": w.now(),
                    "상황": label,
                    "고른 방식": lg.HAND_CHOICE[got],
                    "맞음": got == right,
                    "손 위치 mm": None
                    if k == "none"
                    else [
                        random.randint(280, 330),
                        random.randint(-220, -170),
                        random.randint(90, 140),
                    ],
                }
            )
            w.add_trial(
                f"손 위 전달: {label}", "SUCCESS" if got == right else "FAILED", c["wait"], "H4"
            )
    if d["hand"]:
        r = d["hand"][-1]
        (st.success if r["맞음"] else st.error)(f"{r['상황']} → {r['고른 방식']}")
    st.metric("맞게 고른 비율", lg.pct_ci(sum(x["맞음"] for x in d["hand"]), len(d["hand"])))
    w.table(d["hand"][::-1])
    w.cfg_box("hand")
    w.save_bar("hand", "손 위 전달", "D-08 전달 방식 선택", d["hand"])


def cloth() -> None:
    d = w.td()
    st.caption(
        "D-07: 손수건이 어떻게 놓였는지 판단해 필요한 동작만 고릅니다. 아래 버튼 = '실제로 이렇게 놓았다'(정답)."
    )
    cols = st.columns(4)
    for col, (k, label) in zip(cols, lg.CLOTH.items(), strict=True):
        if col.button(f"{label} 놓기", key=f"cs_{k}"):
            others = [x for x in lg.CLOTH if x != k]
            guess = k if random.random() > 0.15 else random.choice(others)
            d["cloth"].append(
                {
                    "t": w.now(),
                    "실제": label,
                    "판단": lg.CLOTH[guess],
                    "맞음": guess == k,
                    "고른 동작": " → ".join(lg.cloth_steps(guess)) or '하지 않음 · "펴 주세요"',
                }
            )
            w.add_trial(f"손수건 상태: {label}", "SUCCESS" if guess == k else "FAILED", 0.8, "H4")
    st.metric("판단 정확도", lg.pct_ci(sum(x["맞음"] for x in d["cloth"]), len(d["cloth"])))
    w.table(d["cloth"][::-1])
    w.save_bar("cloth", "손수건 상태 판단", "D-07 초기 상태 판단 · 동작 선택", d["cloth"])


PAGES = {"mic": mic, "vision": vision, "coord": coord, "hand": hand, "cloth": cloth}
