"""Thursday 한방 — 여러 화면이 같이 쓰는 도구.

작업별 데이터 · 공통 저장 줄 · 설정 상자 · 지금 팔(Mock).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from app.ui import records

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"  # Git 제외 폴더 (interfaces.md 0장)
HANBANG_DIR = LOG_DIR / "hanbang"  # 사진 · 작업 설명서 초안 · 칸 (팀 합의 전 임시 저장)
MOCKUP_URL = "https://claude.ai/artifact/22pujVnkdhUZArSury9B8i"

JL = ["1 받침", "2 어깨", "3 팔꿈치", "4 손목 꺾기", "5 손목 돌리기", "6 그리퍼 %"]
JMIN = [-110, -100, -97, -95, -157, 0]  # 관절 허용 범위 (도, 그리퍼는 %) — so101.urdf 기준
JMAX = [110, 100, 97, 95, 163, 100]
REST = [0, -60, 60, 40, 0, 10]


def now() -> str:
    return time.strftime("%H:%M:%S")


def clamp_joints(j: list[float]) -> list[int]:
    return [int(round(max(lo, min(hi, v)))) for v, lo, hi in zip(j, JMIN, JMAX, strict=True)]


def _new_task_data(task: str) -> dict:
    d = {
        "poses": [{"n": "대기", "j": list(REST), "spd": None, "memo": "", "runs": [], "edits": []}],
        "demos": [],
        "jsnaps": [],
        "dsets": [],
        "mic": [],
        "vis": [],
        "coords": [],
        "hand": [],
        "cloth": [],
        "thinks": [],
        "confirms": [],
        "gate_runs": [],
        "safety": [],
        "usage": [],
        "trials": [],
        "cmp": [],
        "sessions": [],
        "layout_runs": [],
        "manual": {
            "name": task,
            "objects": [],
            "order": [],
            "steps": [],
            "setup": "",
            "notes": "",
            "ver": [],
        },
        "prog": None,
        "cfg": {},
        "cfg_prev": {},
        "cfg_hist": {},
    }
    if task == "block_a":
        d["manual"].update(
            name="블록 작업 A안",
            objects=[
                "block_tray",
                "block_blue",
                "block_yellow",
                "block_red",
                "block_green",
                "block_orange",
                "block_white",
            ],
            order=["blue", "yellow", "red", "green", "orange", "white"],
            setup="block_tray → T",
            notes="사용자 쪽 칸(A1)부터 먼 쪽으로 순서대로 놓는다",
        )
    if task == "fold_cloth":
        d["manual"].update(
            name="손수건 개기",
            objects=["cloth"],
            steps=[
                "초기 상태 보기 (접힌 모서리)",
                "접힌 모서리 펴기",
                "반 접기",
                "반 접기",
                "결과 확인",
            ],
            notes="모서리 한두 개가 접힌 상태까지만. 구긴 천은 범위 밖 (D-07)",
        )
    return d


def td(task: str | None = None) -> dict:
    """작업별 데이터 (세션 동안 화면에 쌓이는 기록). 남기려면 저장 줄의 "저장"."""
    ss = st.session_state
    task = task or ss.task
    ss.setdefault("data", {})
    if task not in ss.data:
        ss.data[task] = _new_task_data(task)
    return ss.data[task]


def joints() -> list[int]:
    """지금 팔로워 관절값 (Mock). 실제 팔 연결은 app/hw 가 생기면 그 값을 읽음."""
    ss = st.session_state
    ss.setdefault("jf", list(REST))
    ss.setdefault("jl", list(REST))
    return ss.jf


def add_trial(what: str, res: str, sec: float, h: str = "", **kw) -> None:
    td()["trials"].append(
        {"t": now(), "what": what, "res": res, "sec": round(sec, 2), "h": h, **kw}
    )


# ---------------- 공통 저장 줄 ----------------
def _kst(t: float) -> pd.Timestamp:
    return pd.to_datetime(t, unit="s", utc=True).tz_convert("Asia/Seoul")


def save_bar(kind: str, title: str, desc: str, data, task_id: str | None = None, rows=None) -> None:
    """모든 화면 아래: 저장(메모·태그) · 내려받기(JSON) · 실험 기록 초안(.md).

    data = 지금 화면의 기록 (저장하면 logs/<kind>.jsonl 에 한 줄로 남음)
    rows = 초안 결과 표에 넣을 (지표, 값) 목록
    """
    task_id = task_id or st.session_state.task
    with st.container(border=True):
        st.markdown(f"**저장** · `logs/{kind}.jsonl`")
        c1, c2, c3, c4 = st.columns([3, 1, 1.4, 1.6])
        tag = c1.text_input(
            "메모·태그",
            key=f"tag_{kind}_{task_id}",
            placeholder="1차_오전",
            label_visibility="collapsed",
        )
        if c2.button("저장", key=f"sv_{kind}_{task_id}", type="primary"):
            records.append(kind, task_id, {"items": data}, tag=tag, log_dir=LOG_DIR)
            st.toast(f"저장됨 → logs/{kind}.jsonl")
        c3.download_button(
            "⤓ 내려받기 (JSON)",
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            file_name=f"{task_id}_{kind}.json",
            mime="application/json",
            key=f"dl_{kind}_{task_id}",
        )
        md = records.draft_md(
            f"{task_id} · {title}",
            purpose=desc,
            rows=rows or [("기록 수", str(len(data) if hasattr(data, "__len__") else 1))],
            source=f"logs/{kind}.jsonl",
        )
        c4.download_button(
            "기록 초안 (.md)",
            md,
            file_name=f"{task_id}_{kind}_draft.md",
            mime="text/markdown",
            key=f"md_{kind}_{task_id}",
        )
        saved = records.read(kind, task_id, log_dir=LOG_DIR)
        if saved:
            st.caption(
                "저장 이력: "
                + " / ".join(
                    f"{_kst(r['t']):%m-%d %H:%M} · {r['tag'] or '태그 없음'}"
                    for r in saved[-4:][::-1]
                )
            )


# ---------------- 설정 상자 (범위 · 바꾼 기록 · 되돌리기) ----------------
CFG = {
    "mic": [
        ("listen", "듣는 방식", ["ptt", "always"], "ptt"),
        ("min_conf", "이 % 아래면 되묻기", (50, 95, 1), 70),
    ],
    "vision": [
        ("min_conf", "확신 기준 %", (30, 95, 1), 60),
        ("frames", "몇 장 연속이면 인정", (1, 10, 1), 3),
    ],
    "hand": [
        ("wait", "손 기다리는 시간 (초)", (1.0, 6.0, 0.5), 3.5),
        ("above", "손 위 몇 cm 에서 놓기", (2, 10, 1), 5),
    ],
    "gate": [("max_steps", "최대 단계 수", (4, 20, 1), 12), ("retry", "재시도 횟수", (0, 3, 1), 2)],
    "confirm": [
        ("mode", "실행 방식", ["confirm", "auto"], "confirm"),
        ("near_h", "자동이어도 H 근처는 묻기", ["on", "off"], "on"),
    ],
    "layout": [
        ("alpha", "사용 기록 비중 α", (0.0, 1.0, 0.1), 0.7),
        ("beta", "공간 비중 β", (0.0, 1.0, 0.1), 0.3),
    ],
    "progress": [("frames", "같은 상태 몇 장이면 사건", (1, 10, 1), 3)],
    "live": [
        ("mode", "실행 방식", ["confirm", "auto"], "confirm"),
        ("photos", "카메라 사진도 저장", ["off", "on"], "off"),
    ],
    "teach": [
        ("spd", "재생 속도 %", (5, 30, 1), 20),
        ("wait", "자세 사이 대기 (초)", (0.0, 3.0, 0.1), 0.5),
    ],
}
OPT_KO = {
    "ptt": "누르는 동안만 (기본)",
    "always": "상시 대기 (호출어)",
    "confirm": "확인 모드 (기본)",
    "auto": "자동 모드",
    "on": "예",
    "off": "아니오",
}


def cfg(key: str) -> dict:
    d = td()
    if key not in d["cfg"]:
        d["cfg"][key] = {k: default for k, _, _, default in CFG[key]}
    return d["cfg"][key]


def cfg_box(key: str, note: str = "허용 범위 안에서만 바뀝니다 · 바꾼 기록과 되돌리기") -> dict:
    d, cur = td(), cfg(key)
    with st.container(border=True):
        st.markdown(f"**설정** · {note}")
        new = {}
        for k, label, rng, _ in CFG[key]:
            wkey = f"cf_{st.session_state.task}_{key}_{k}"
            if isinstance(rng, list):
                new[k] = st.selectbox(
                    label,
                    rng,
                    index=rng.index(cur[k]),
                    format_func=lambda v: OPT_KO.get(v, v),
                    key=wkey,
                )
            else:
                lo, hi, step = rng
                new[k] = st.slider(label, lo, hi, cur[k], step, key=wkey)
        c1, c2 = st.columns(2)
        if c1.button("적용", key=f"cfa_{key}"):
            ch = [f"{lab}: {cur[k]} → {new[k]}" for k, lab, _, _ in CFG[key] if new[k] != cur[k]]
            if ch:
                d["cfg_prev"][key] = dict(cur)
                cur.update(new)
                d["cfg_hist"].setdefault(key, [])[:0] = [f"{now()} {c}" for c in ch]
                st.toast("적용됨")
            else:
                st.toast("바뀐 값이 없습니다")
        if c2.button("되돌리기", key=f"cfu_{key}"):
            if d["cfg_prev"].get(key):
                cur.update(d["cfg_prev"][key])
                d["cfg_prev"][key] = None
                d["cfg_hist"].setdefault(key, []).insert(0, f"{now()} 이전 설정으로 되돌림")
                for k, *_ in CFG[key]:
                    st.session_state.pop(f"cf_{st.session_state.task}_{key}_{k}", None)
                st.rerun()
            else:
                st.toast("되돌릴 변경이 없습니다")
        if d["cfg_hist"].get(key):
            st.caption("바꾼 기록: " + " · ".join(d["cfg_hist"][key][:4]))
    return cur


def table(rows: list[dict], empty: str = "아직 없습니다.") -> None:
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    else:
        st.caption(empty)
