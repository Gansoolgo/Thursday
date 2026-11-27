# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""0 공통 설정 (작업대 지도 제외) — 0-2 물건 등록 · 0-3 카메라 보정 · 0-4 스킬 목록 · 0-5 시작 전 점검 · 0-6 장치 부하.

공통 파일(config/*.yaml)은 건드리지 않고 logs/hanbang/ 에 저장합니다 (팀 합의 후 config/ 로).
"""

from __future__ import annotations

import random
import time

import streamlit as st

from app.ui import records
from app.ui import slots as sl
from app.ui import widgets as w

DEFAULT_OBJECTS = [
    ("block_tray", "블록 트레이", "big", "T"),
    ("block_blue", "파랑 블록", "small", "S1"),
    ("block_yellow", "노랑 블록", "small", "S2"),
    ("block_red", "빨강 블록", "small", ""),
    ("block_green", "초록 블록", "small", ""),
    ("block_orange", "주황 블록", "small", ""),
    ("block_white", "하양 블록", "small", ""),
    ("resistor_case", "저항 케이스", "big", "S3"),
    ("cloth", "손수건", "big", ""),
]
SKILLS = [
    ("detect_objects", "없음", "카메라 정상", "인식 목록 갱신", "모든 작업"),
    (
        "pick_place",
        "object_id, slot_id",
        "대상 있음 · 칸 비었음 · 범위 안",
        "물건이 목표 칸에 있음",
        "block_a",
    ),
    ("hand_over", "object_id", "H 비었음", "H(또는 손 위)에 있음", "block_a, safety"),
    ("optimize_layout", "없음", "사용 기록 있음", "칸 배정표", "block_a"),
    ("verify_result", "object_id, slot_id", "최신 영상", "목표와 일치", "모든 작업"),
    ("unfold_corner", "cloth", "접힌 모서리 보임", "모서리 펴짐", "fold_cloth"),
    ("fold_half", "cloth", "펴진 손수건", "반으로 접힘", "fold_cloth"),
]
CHECKS = [
    ("cam_left", "카메라 1 왼쪽 암"),
    ("cam_right", "카메라 2 오른쪽 암"),
    ("cam_side", "카메라 3 측면 (HP60C ②)"),
    ("cam_top", "카메라 4 위 (HP60C ①)"),
    ("mic", "마이크"),
    ("robot", "로봇 연결 · 보정"),
    ("llm", "AI 계획 모델 (OpenVINO GenAI)"),
    ("vision", "물체 인식 모델"),
    ("estop", "비상 정지 (안 눌림)"),
    ("map", "작업대 지도 (칸이 팔 범위 · 작업대 안)"),
]
CALCAM = [
    ("top", "4 위 (HP60C ①)"),
    ("side", "3 측면 (HP60C ②)"),
    ("left", "1 왼쪽 암 손목"),
    ("right", "2 오른쪽 암 손목"),
]
LOADM = [
    ("asr", "음성 인식 (Whisper)"),
    ("vis", "물체 인식 (NPU)"),
    ("llm", "AI 계획 (내장 GPU)"),
    ("cams", "카메라 4대 받기"),
]


def objects_list() -> list[dict]:
    ss = st.session_state
    if "objects" not in ss:
        ss.objects = [
            {"id": i, "이름": n, "크기": s, "제자리": h} for i, n, s, h in DEFAULT_OBJECTS
        ]
    return ss.objects


def objects() -> None:
    ss = st.session_state
    st.caption(
        "로봇이 다룰 수 있는 물건 목록입니다. 여기에 없는 물건은 안전 검사 4번에서 거절됩니다. ID 는 고정, 이름 · 크기 · 제자리는 바꿀 수 있습니다."
    )
    ids = [s.id for s in (ss.get("slots") or sl.default_slots()) if s.zone != "handover_zone"]
    edited = st.data_editor(
        objects_list(),
        column_config={
            "id": st.column_config.TextColumn("ID (고정)", disabled=True),
            "크기": st.column_config.SelectboxColumn("크기", options=["small", "big"]),
            "제자리": st.column_config.SelectboxColumn("제자리 칸", options=[""] + ids),
        },
        hide_index=True,
        key="obj_ed",
    )
    ss.objects = [dict(x) for x in edited]
    c1, c2, c3 = st.columns([2, 2, 1])
    nid = c1.text_input("새 물건 ID", placeholder="block_purple")
    nname = c2.text_input("이름", placeholder="보라 블록")
    if c3.button("추가", type="primary"):
        import re

        if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", nid.strip()):
            st.error("ID 는 영어 소문자·숫자·_ 로 2~32자 (예: block_purple)")
        elif any(o["id"] == nid.strip() for o in ss.objects):
            st.error("이미 있는 ID 입니다")
        else:
            ss.objects.append(
                {
                    "id": nid.strip(),
                    "이름": nname.strip() or nid.strip(),
                    "크기": "small",
                    "제자리": "",
                }
            )
            st.rerun()
    if st.button("objects.yaml 로 저장"):
        import yaml

        path = w.HANBANG_DIR / "objects.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            o["id"]: {"display_name": o["이름"], "size": o["크기"], "home": o["제자리"] or None}
            for o in ss.objects
        }
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        st.success(f"저장됨 → {path.relative_to(w.ROOT)} (팀 합의 후 config/objects.yaml 로)")
    w.save_bar("objects", "물건 등록", "다룰 수 있는 물건 목록", ss.objects, task_id="common")


def calib() -> None:
    ss = st.session_state
    ss.setdefault("calib", {})
    st.caption(
        "작업대에 ArUco 마커(인쇄한 네모 무늬)를 놓고 카메라 좌표와 로봇 좌표가 몇 mm 어긋나는지 잽니다 (US-09). "
        "**카메라를 움직이면 다시 해야 합니다.** 깊이 카메라라 두 카메라 사이 보정은 필요 없습니다 (D-15). 지금은 Mock."
    )
    for k, n in CALCAM:
        h = ss.calib.get(k, [])
        last = h[-1] if h else None
        c1, c2 = st.columns([4, 1])
        c1.write(
            f"**{n}** · "
            + (
                f"{last['t']} · 평균 {last['err']} mm · 최대 {last['max']} mm · 점 {last['pts']}"
                + (" ⚠ 8 mm 넘음" if last["err"] > 8 else "")
                if last
                else "아직 안 함"
            )
        )
        if c2.button("보정 실행", key=f"cal_{k}"):
            with st.spinner("마커 6개 찾는 중…"):
                time.sleep(0.6)
            e = round(random.uniform(2, 9.5), 1)
            ss.calib.setdefault(k, []).append(
                {"t": w.now(), "err": e, "max": round(e * 1.8, 1), "pts": 6}
            )
            st.rerun()
    st.caption("통과 기준은 #5 spike 결과로 정함 (확인 필요)")
    w.save_bar("calib", "카메라 보정", "카메라 ↔ 로봇 오차 mm", ss.calib, task_id="common")


def skills() -> None:
    st.caption(
        "로봇이 할 줄 아는 동작입니다. AI 계획은 이 목록 안에서만 고르고, 없는 동작은 안전 검사 3번에서 거절됩니다. "
        "새 작업에 새 동작이 필요하면 Skill 만 추가하고 엔진(Planner · Safety Gate · Action Manager)은 고치지 않습니다."
    )
    trials = [t for d in st.session_state.get("data", {}).values() for t in d["trials"]]
    rows = []
    for name, args, pre, ok, tasks in SKILLS:
        mine = [t for t in trials if name in t["what"]]
        rows.append(
            {
                "Skill": name,
                "인자": args,
                "실행 조건": pre,
                "성공 판정": ok,
                "쓰는 작업": tasks,
                "시험 수": len(mine),
                "성공": sum(t["res"] == "SUCCESS" for t in mine),
            }
        )
    w.table(rows)
    st.caption("공통 결과: SUCCESS / FAILED / UNAVAILABLE / HOLD · 실패 코드는 interfaces.md 8장")
    w.save_bar("skills", "스킬 목록", "Skill Registry", rows, task_id="common")


def run_checks(placeholder=None, fail_cam: bool = False) -> list[dict]:
    """시작 전 점검. 지금은 Mock — 하드웨어 모듈이 생기면 실제로 확인."""
    ss = st.session_state
    slots, robots = ss.get("slots") or sl.default_slots(), ss.get("robots") or sl.ROBOTS
    out = []
    for cid, name in CHECKS:
        ok, note = True, "Mock"
        if cid == "cam_side" and fail_cam:
            ok, note = False, "응답 없음 (USB 확인)"
        if cid == "estop" and ss.get("estop"):
            ok, note = False, "눌린 상태 — 왼쪽에서 풀어 주세요"
        if cid == "map":
            bad = [
                s.id for s in slots if not sl.in_reach(s, ss.get("reach", 330.0), robots)
            ] + sl.outside_table(slots)
            ok, note = not bad, ("문제: " + ", ".join(bad)) if bad else "실제 계산"
        out.append({"점검": name, "결과": "정상" if ok else "문제", "메모": note})
        if placeholder is not None:
            placeholder.dataframe(out, hide_index=True, width="stretch")
            time.sleep(0.12)
    return out


def precheck() -> None:
    ss = st.session_state
    st.caption(
        "자율 모드(99)를 켜면 이 점검이 먼저 돌고, 하나라도 문제면 시작하지 않습니다. 시연 · 리허설 전에도 여기서 확인하세요."
    )
    fail = st.checkbox("실패 흉내 (카메라 3번 연결 안 됨) — 시험용", key="pc_fail")
    ph = st.empty()
    if st.button("점검 시작", type="primary"):
        ss.checks = run_checks(ph, fail)
        records.append("precheck", "common", {"items": ss.checks}, log_dir=w.LOG_DIR)
    if ss.get("checks"):
        ph.dataframe(ss.checks, hide_index=True, width="stretch")
        bad = [c["점검"] for c in ss.checks if c["결과"] != "정상"]
        (st.error if bad else st.success)(
            "문제가 있어 시작하지 않습니다: " + ", ".join(bad)
            if bad
            else "모두 정상 — 시작할 수 있어요"
        )
    w.save_bar(
        "precheck", "시작 전 점검", "장치 점검 결과", ss.get("checks") or [], task_id="common"
    )


def load() -> None:
    ss = st.session_state
    ss.setdefault("load_peak", {})
    st.caption(
        "음성 · 인식 · AI 가 동시에 돌 때 노트북 한 대(Core Ultra 5 225H)가 버티는지 봅니다 (D-05 · #30). 지금은 예시 값 — 실제 측정은 #30."
    )
    cols = st.columns(4)
    on = {k: cols[i].toggle(n, value=k != "llm", key=f"ld_{k}") for i, (k, n) in enumerate(LOADM)}
    base = {
        "CPU": 12 + 18 * on["asr"] + 14 * on["cams"] + 5 * on["vis"] + 10 * on["llm"],
        "내장 GPU": 4 + 62 * on["llm"] + (6 if on["vis"] and not on["llm"] else 0),
        "NPU": 2 + 48 * on["vis"],
        "메모리": 28 + 34 * on["llm"] + 8 * on["asr"] + 4 * on["vis"] + 4 * on["cams"],
    }
    for k, v in base.items():
        v = max(0, min(100, v + random.randint(-4, 4)))
        ss.load_peak[k] = max(ss.load_peak.get(k, 0), v)
        st.progress(v / 100, text=f"{k} {v}%" + (" ⚠" if v >= 70 else ""))
    st.caption(
        "최고: " + " · ".join(f"{k} {v}%" for k, v in ss.load_peak.items()) + " · 70% 넘으면 ⚠"
    )
    if st.button("최고값 지우기"):
        ss.load_peak = {}
        st.rerun()
    w.save_bar("load", "장치 부하", "동시 실행 부하 (D-05)", ss.load_peak, task_id="common")


PAGES = {"objects": objects, "calib": calib, "skills": skills, "precheck": precheck, "load": load}
