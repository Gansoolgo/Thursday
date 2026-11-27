"""Thursday 한방 v0 — 팀 기록·시험 툴 (Issue #46, #18 첫 조각)

실행 (PowerShell, 레포 맨 위 폴더에서):
    python -m pip install -r requirements.txt -r requirements-dev.txt
    python -m streamlit run app/ui/hanbang.py
→ 브라우저가 열립니다 (http://localhost:8501). 끌 때는 터미널에서 Ctrl+C.

순서 (승인된 클릭 시안 v7 과 같은 메뉴):
    왼쪽: 1~3 작업 · 새 작업 · 0 공통 설정 · 번호 이동 (예: 2-1, 99, 0-1)
    작업 안: 메뉴 1 (묶음 1~5, 99) → 메뉴 2 (항목)
모든 항목이 동작합니다. 로봇 · 카메라 · 음성 인식 · AI 계획은 아직 Mock(예시 값)이고,
진짜 모듈(app/hw, Planner, Safety Gate …)이 생기면 그 결과를 보여 주도록 바꿉니다.
화면 파일: pages_teach(1) · pages_sense(2) · pages_think(3) · pages_flow(4) · pages_result(5)
          · pages_auto(99) · pages_common(0-2~0-6) · views(아래 보기)
          · 이 파일(메뉴 · 0-1 작업대 지도)

고칠 숫자 (맨 위 상수):
    REACH_MM  닿는 범위 기본값 (실측 전 330 mm)
    LOG_DIR / SLOTS_PATH  저장 위치 (logs/ 는 Git 제외 · config/slots.yaml 은 팀 합의 후)

실제 로봇 · 카메라는 쓰지 않습니다 (하드웨어 없음). 왼쪽 ■ 정지는 Mock 상태만 멈춥니다.
"""

from __future__ import annotations

import importlib
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # streamlit run 은 이 파일 폴더만 경로에 넣으므로 레포 맨 위를 추가
    sys.path.insert(0, str(ROOT))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.ui import records  # noqa: E402
from app.ui import slots as sl  # noqa: E402
from app.ui import widgets as w  # noqa: E402

# 묶음 화면 파일 (PR 을 묶음별로 나눠 올려서, 아직 병합 전인 파일은 "병합 대기" 로 보여 줌)
GROUP_MODULE = {
    1: "pages_teach",
    2: "pages_sense",
    3: "pages_think",
    4: "pages_flow",
    5: "pages_result",
}


def page_module(name: str):
    """app.ui.<name> 을 불러온다. 그 파일이 아직 없으면 None."""
    try:
        return importlib.import_module(f"app.ui.{name}")
    except ModuleNotFoundError as e:
        if e.name != f"app.ui.{name}":
            raise  # 파일은 있는데 안에서 필요한 패키지가 없는 경우는 그대로 알림
        return None


def not_merged(name: str) -> None:
    st.info(
        f"이 화면(`app/ui/{name}.py`)은 아직 병합 전입니다. "
        "묶음별 PR 이 순서대로 병합되면 나타납니다."
    )


REACH_MM = 330.0
LOG_DIR = ROOT / "logs"
SLOTS_PATH = ROOT / sl.DEFAULT_PATH
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,23}$")

TASKS = {"block_a": "블록 작업", "fold_cloth": "손수건 개기", "safety": "안전 실험"}
GROUPS = [
    (
        1,
        "가르치기",
        "동작을 가르치고 남기기",
        [
            ("teach", "티칭"),
            ("demo", "리더암 시범"),
            ("jhist", "관절값 저장 기록"),
            ("ds", "모방학습 데이터"),
        ],
    ),
    (
        2,
        "듣기·보기 시험",
        "귀와 눈이 제대로 받는지",
        [
            ("mic", "마이크·음성"),
            ("vision", "물체 인식"),
            ("coord", "카메라 좌표"),
            ("hand", "손 위치 · 손 위 전달"),
        ],
    ),
    (
        3,
        "생각·안전",
        "어떻게 판단하고 위험은 막는지",
        [
            ("think", "생각 과정"),
            ("confirm", "확인 모드"),
            ("gate", "안전 검사 세트"),
            ("safety", "손 보이면 정지 실험"),
        ],
    ),
    (
        4,
        "작업 진행",
        "작업이 순서대로 흘러가는지",
        [
            ("manual", "작업 설명서"),
            ("progress", "단계 추정 · 순서 이탈"),
            ("layout", "정리 시뮬레이션"),
        ],
    ),
    (
        5,
        "기록·결과",
        "숫자로 증명",
        [
            ("usage", "사용 기록"),
            ("trial", "시험 기록 · 정답"),
            ("compare", "비교 모드"),
            ("summary", "결과 요약"),
        ],
    ),
]
COMMON = [
    ("map", "작업대 지도"),
    ("objects", "물건 등록"),
    ("calib", "카메라 보정"),
    ("skills", "스킬 목록"),
    ("precheck", "시작 전 점검"),
    ("load", "장치 부하"),
]
ZONE_COLOR = {
    "storage": "#87919a",
    "work": "#2a63c9",
    "assembly": "#1f8a5b",
    "handover": "#e07b2e",
    "return": "#4fa89b",
    "handover_zone": "#e5a54a",
}


def groups_for(task: str):
    """손수건 작업만 2-4 가 '손수건 상태 판단'."""
    out = []
    for no, name, desc, items in GROUPS:
        if task == "fold_cloth":
            items = [("cloth", "손수건 상태 판단") if k == "hand" else (k, n) for k, n in items]
        out.append((no, name, desc, items))
    return out


# ---------------- 상태 ----------------
def init_state() -> None:
    ss = st.session_state
    if "sec" in ss:
        return
    ss.sec, ss.task, ss.grp, ss.item = "home", "block_a", None, None
    ss.tasks = dict(TASKS)
    ss.slots = sl.load(SLOTS_PATH) if SLOTS_PATH.exists() else sl.default_slots()
    ss.undo, ss.hist, ss.reach, ss.sel = [], [], REACH_MM, "S1"
    ss.robots = dict(sl.ROBOTS)


def nav(**kw) -> None:
    st.session_state.update(kw)
    st.rerun()


def parse_jump(text: str) -> dict | str:
    """번호 이동. 성공이면 바꿀 상태(dict), 실패면 안내 문장(str)."""
    s, ss = text.strip(), st.session_state
    ids = list(ss.tasks)
    if s == "0":
        return {"sec": "common", "item": None}
    m = re.fullmatch(r"0-(\d+)", s)
    if m and 1 <= int(m[1]) <= len(COMMON):
        return {"sec": "common", "item": COMMON[int(m[1]) - 1][0]}
    if ss.sec == "task":
        if s == "99":
            return {"grp": 99, "item": None}
        m = re.fullmatch(r"([1-5])-(\d+)", s)
        if m:
            g = next(x for x in groups_for(ss.task) if x[0] == int(m[1]))
            if 1 <= int(m[2]) <= len(g[3]):
                return {"grp": g[0], "item": g[3][int(m[2]) - 1][0]}
        if re.fullmatch(r"[1-5]", s):
            return {"grp": int(s), "item": None}
        return "작업 안: 1~5 (묶음), 2-1 (항목), 99, 0-1 · 다른 작업은 위 목록에서"
    if s.isdigit() and 1 <= int(s) <= len(ids):
        return {"sec": "task", "task": ids[int(s) - 1], "grp": None, "item": None}
    return f"1~{len(ids)} (작업), 0 또는 0-1 (공통 설정)"


# ---------------- 화면들 ----------------
def sidebar() -> None:
    ss = st.session_state
    with st.sidebar:
        st.title("Thursday 한방")
        st.caption("v0 · 로봇 · 카메라 Mock")
        stop = ss.get("estop", False)
        if st.button("정지 풀기" if stop else "■ 정지", type="primary", width="stretch"):
            ss.estop = not stop
            st.rerun()
        if stop:
            st.error("정지 상태 — 자율 모드 · 재생이 멈춰 있습니다")
        st.markdown("**작업**")
        for i, (tid, name) in enumerate(ss.tasks.items(), 1):
            on = ss.sec == "task" and ss.task == tid
            if st.button(
                f"{i}  {tid} · {name}",
                key=f"t_{tid}",
                type="primary" if on else "secondary",
                width="stretch",
            ):
                nav(sec="task", task=tid, grp=None, item=None)
        with st.expander("＋ 새 작업"):
            new = st.text_input("작업 이름", placeholder="pick_tool", key="new_task")
            if st.button("추가", key="new_ok"):
                if not NAME_RE.match(new.strip()):
                    st.error("영어 소문자·숫자·_ 로 2~24자 (예: pick_tool)")
                elif new.strip() in ss.tasks:
                    st.error("이미 있는 작업입니다")
                else:
                    ss.tasks[new.strip()] = "새 작업"
                    nav(sec="task", task=new.strip(), grp=4, item="manual")
        st.markdown("**공통**")
        if st.button(
            "0  공통 설정",
            type="primary" if ss.sec == "common" else "secondary",
            width="stretch",
        ):
            nav(sec="common", item=None)
        st.markdown("**번호 이동**")
        c1, c2 = st.columns([2, 1])
        jump = c1.text_input("번호", placeholder="2-1", label_visibility="collapsed", key="jump")
        if c2.button("이동"):
            r = parse_jump(jump)
            if isinstance(r, dict):
                nav(**r)
            st.error(r)


def crumbs() -> None:
    ss = st.session_state
    parts = ["메뉴"]
    if ss.sec == "task":
        parts.append(f"{list(ss.tasks).index(ss.task) + 1} {ss.task}")
        if ss.grp == 99:
            parts.append("99 자율 모드")
            if ss.item:
                parts.append({"live": "99-1 켜기", "sessions": "99-2 세션 기록"}[ss.item])
        elif ss.grp:
            g = next(x for x in groups_for(ss.task) if x[0] == ss.grp)
            parts.append(f"{g[0]} {g[1]}")
            if ss.item:
                i = [k for k, _ in g[3]].index(ss.item)
                parts.append(f"{g[0]}-{i + 1} {g[3][i][1]}")
    elif ss.sec == "common":
        parts.append("0 공통 설정")
        if ss.item:
            i = [k for k, _ in COMMON].index(ss.item)
            parts.append(f"0-{i + 1} {COMMON[i][1]}")
    st.caption(" › ".join(parts))


def home() -> None:
    ss = st.session_state
    st.header("번호를 고르세요")
    st.caption(
        "왼쪽 번호를 누르거나 번호 칸에 넣고 이동하세요. "
        "작업 안에서는 2 (묶음), 2-1 (항목), 99, 0-1 처럼 씁니다."
    )
    cols = st.columns(3)
    for i, (tid, name) in enumerate(ss.tasks.items()):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{i + 1} · `{tid}`**  \n{name}")
            if st.button("열기", key=f"open_{tid}"):
                nav(sec="task", task=tid, grp=None, item=None)


def task_page() -> None:
    ss = st.session_state
    gs = groups_for(ss.task)
    st.header(f"{list(ss.tasks).index(ss.task) + 1} · {ss.task}")
    cols = st.columns(len(gs) + 1)
    for c, (no, name, _, _) in zip(cols, gs, strict=False):
        if c.button(
            f"{no} {name}",
            key=f"g_{no}",
            type="primary" if ss.grp == no else "secondary",
            width="stretch",
        ):
            nav(grp=no, item=None)
    if cols[-1].button(
        "99 자율 모드", type="primary" if ss.grp == 99 else "secondary", width="stretch"
    ):
        nav(grp=99, item=None)

    if ss.grp is None:
        st.caption("메뉴 1 — 비슷한 것끼리 묶었습니다. 묶음을 누르면 안의 항목(메뉴 2)이 나옵니다.")
        for no, name, desc, items in gs:
            st.markdown(
                f"**{no} {name}** — {desc}: "
                + " · ".join(f"{no}-{i} {n}" for i, (_, n) in enumerate(items, 1))
            )
    elif ss.grp == 99:
        sub = st.columns(2)
        for c, (k, n) in zip(
            sub, [("live", "99-1 켜기"), ("sessions", "99-2 세션 기록")], strict=True
        ):
            if c.button(
                n,
                key=f"i99_{k}",
                type="primary" if ss.item == k else "secondary",
                width="stretch",
            ):
                nav(item=k)
        m = page_module("pages_auto")
        if m is None:
            not_merged("pages_auto")
        elif ss.item == "sessions":
            m.sessions()
        else:
            m.live()
    else:
        no, name, desc, items = next(x for x in gs if x[0] == ss.grp)
        sub = st.columns(len(items))
        for i, (c, (k, n)) in enumerate(zip(sub, items, strict=False), 1):
            if c.button(
                f"{no}-{i} {n}",
                key=f"i_{k}",
                type="primary" if ss.item == k else "secondary",
                width="stretch",
            ):
                nav(item=k)
        m = page_module(GROUP_MODULE[no])
        if ss.item and m is None:
            not_merged(GROUP_MODULE[no])
        elif ss.item and ss.item in m.PAGES:
            st.subheader(dict(items)[ss.item])
            m.PAGES[ss.item]()
        else:
            st.caption(f"메뉴 2 — {desc}. 항목을 고르세요.")
    v = page_module("views")
    if v is not None:
        v.views()


def zone_label(z: str) -> str:
    return sl.ZONES.get(z, z)


def map_chart(
    slots: list[sl.Slot], sel: str, reach: float, robots: dict[str, tuple[float, float]]
) -> alt.LayerChart:
    """위에서 본 작업대: 위 = 뒤쪽(로봇 A · B), 아래 = 앞쪽(사람), 오른쪽 = +y."""
    depth, width = sl.TABLE_MM
    off = set(sl.outside_table(slots))
    rows = []
    for s in slots:
        x, y, _ = s.center_mm
        dx, dy = s.size_mm[0] / 2, s.size_mm[1] / 2
        arms = sl.reach_by(s, reach, robots)
        rows.append(
            {
                "id": s.id,
                "name": s.name,
                "zone": zone_label(s.zone),
                "x1": x - dx,
                "x2": x + dx,
                "y1": y - dy,
                "y2": y + dy,
                "cx": x,
                "cy": y,
                "bad": s.id in off or not sl.in_reach(s, reach, robots),
                "sel": s.id == sel,
                "arms": ", ".join(arms) if s.zone != "handover_zone" else "(넓은 영역)",
            }
        )
    df = pd.DataFrame(rows)
    xs = alt.Scale(domain=[-20, width + 20])  # 오른쪽 = +y (원점 = 왼쪽 뒤 모서리)
    ys = alt.Scale(domain=[-50, depth + 60], reverse=True)  # 위 = 뒤쪽(로봇), 아래 = 사람
    color = alt.Color(
        "zone:N",
        scale=alt.Scale(
            domain=[zone_label(z) for z in ZONE_COLOR], range=list(ZONE_COLOR.values())
        ),
        title="종류",
    )
    table = (
        alt.Chart(pd.DataFrame([{"x1": 0, "x2": depth, "y1": 0, "y2": width}]))
        .mark_rect(fillOpacity=0.04, stroke="#87919a", strokeWidth=2)
        .encode(
            x=alt.X("y1:Q", scale=xs, title="y (mm) · 사람이 볼 때 오른쪽 →"),
            x2="y2:Q",
            y=alt.Y("x1:Q", scale=ys, title="x (mm) · 뒤(로봇) → 앞(사람)"),
            y2="x2:Q",
        )
    )
    rects = (
        alt.Chart(df)
        .mark_rect(opacity=0.5)
        .encode(
            x=alt.X("y1:Q", scale=xs),
            x2="y2:Q",
            y=alt.Y("x1:Q", scale=ys),
            y2="x2:Q",
            color=color,
            stroke=alt.condition("datum.bad", alt.value("#d23a32"), alt.value("#55606a")),
            strokeWidth=alt.condition("datum.sel || datum.bad", alt.value(3), alt.value(1)),
            tooltip=["id", "name", "zone", "cx", "cy", alt.Tooltip("arms", title="닿는 팔")],
        )
    )
    text = (
        alt.Chart(df)
        .mark_text(fontSize=10)
        .encode(x=alt.X("cy:Q", scale=xs), y=alt.Y("cx:Q", scale=ys), text="id")
    )
    pts = pd.DataFrame(
        [
            {
                "arm": name,
                "a": i,
                "x": rx + reach * math.sin(i / 60 * math.pi),
                "y": ry + reach * math.cos(i / 60 * math.pi),
            }
            for name, (rx, ry) in robots.items()
            for i in range(61)
        ]
    )
    circles = (
        alt.Chart(pts)
        .mark_line(strokeDash=[4, 4], color="#1f8a5b", clip=True)
        .encode(x=alt.X("y:Q", scale=xs), y=alt.Y("x:Q", scale=ys), detail="arm:N", order="a:Q")
    )
    marks = pd.DataFrame(
        [{"x": rx, "y": ry, "t": f"로봇 {n}"} for n, (rx, ry) in robots.items()]
        + [{"x": depth + 35, "y": width / 2, "t": "사람"}]
    )
    people = (
        alt.Chart(marks)
        .mark_point(size=260, filled=True, color="#2a63c9")
        .encode(x=alt.X("y:Q", scale=xs), y=alt.Y("x:Q", scale=ys))
    )
    labels = (
        alt.Chart(marks)
        .mark_text(dy=-16, fontSize=11, fontWeight="bold")
        .encode(x=alt.X("y:Q", scale=xs), y=alt.Y("x:Q", scale=ys), text="t")
    )
    return (table + circles + rects + text + people + labels).properties(height=480)


def map_page() -> None:
    ss = st.session_state
    depth, width = sl.TABLE_MM
    st.subheader("0-1 작업대 지도")
    st.caption(
        f"작업대 가로 {width / 10:.0f} cm × 세로 {depth / 10:.0f} cm · 위 = 뒤쪽(로봇 A · B), "
        "아래 = 사람. 칸을 고르고 이름 · 종류 · 좌표를 바꿉니다. **ID 는 고정**, 표시 이름만 "
        "자유롭게 바꿔요 — 프로그램과 기록이 ID 로 칸을 찾기 때문입니다. "
        "초록 점선 = 팔마다 닿는 범위, 빨간 굵은 테두리 = 범위 밖이거나 작업대 밖."
    )
    st.caption(
        "좌표 원점 = 커팅 매트 모서리 ArUco 마커 (D-16). 정확한 모서리 · 축은 #5 에서 정하므로 "
        "지금은 임시로 왼쪽 뒤 모서리(로봇 A 쪽), x = 사람 쪽, y = 사람이 볼 때 오른쪽."
    )
    errs = sl.validate(ss.slots)
    far = [s.id for s in ss.slots if not sl.in_reach(s, ss.reach, ss.robots)]
    off = sl.outside_table(ss.slots)
    for e in errs:
        st.error(e)
    if far:
        st.warning("두 팔 모두 닿지 않는 칸: " + ", ".join(far))
    if off:
        st.warning("작업대 밖으로 나간 칸: " + ", ".join(off))

    left, right = st.columns([3, 2])
    with left:
        st.altair_chart(map_chart(ss.slots, ss.sel, ss.reach, ss.robots), width="stretch")
        ss.reach = float(st.slider("닿는 범위 반지름 (mm, 실측 전)", 200, 400, int(ss.reach), 10))
        with st.expander("로봇 받침 위치 (mm, 실측 전 예시)"):
            new_robots = {}
            for name, (rx, ry) in ss.robots.items():
                c1, c2 = st.columns(2)
                nx = c1.number_input(f"로봇 {name} x (뒤 0)", value=rx, step=5.0, key=f"rx_{name}")
                ny = c2.number_input(f"로봇 {name} y", value=ry, step=5.0, key=f"ry_{name}")
                new_robots[name] = (float(nx), float(ny))
            if new_robots != ss.robots:
                ss.robots = new_robots
                ss.hist.insert(0, "로봇 위치 바꿈")
                st.rerun()
    with right:
        ids = [s.id for s in ss.slots]
        if ss.sel not in ids:
            ss.sel = ids[0]
        ss.sel = st.selectbox(
            "칸 고르기",
            ids,
            index=ids.index(ss.sel),
            format_func=lambda i: f"{i} {sl.get(ss.slots, i).name}".strip(),
        )
        s = sl.get(ss.slots, ss.sel)
        arms = sl.reach_by(s, ss.reach, ss.robots)
        st.caption(
            "닿는 팔: "
            + (
                "넓은 영역이라 검사 안 함"
                if s.zone == "handover_zone"
                else ", ".join(arms) or "없음"
            )
        )
        with st.form(f"slot_{s.id}"):
            st.text_input("ID (고정)", s.id, disabled=True)
            name = st.text_input("표시 이름", s.name, placeholder="저항 케이스")
            zones = list(sl.ZONES)
            zone = st.selectbox(
                "종류",
                zones,
                index=zones.index(s.zone) if s.zone in zones else 0,
                format_func=zone_label,
            )
            c1, c2, c3 = st.columns(3)
            x = c1.number_input("x 앞 (mm)", value=s.center_mm[0], step=5.0)
            y = c2.number_input("y 오른쪽 (mm)", value=s.center_mm[1], step=5.0)
            z = c3.number_input("z 위 (mm)", value=s.center_mm[2], step=1.0)
            c4, c5 = st.columns(2)
            dx = c4.number_input("앞뒤 크기 (mm)", value=s.size_mm[0], step=5.0)
            dy = c5.number_input("좌우 크기 (mm)", value=s.size_mm[1], step=5.0)
            home_obj = st.text_input(
                "제자리 물건 (objects.yaml 키)", s.home or "", placeholder="block_blue"
            )
            if st.form_submit_button("이 칸 바꾸기", type="primary"):
                new = sl.update(
                    ss.slots,
                    s.id,
                    name=name.strip(),
                    zone=zone,
                    center_mm=(x, y, z),
                    size_mm=(dx, dy),
                    home=home_obj.strip() or None,
                )
                problems = sl.validate(new)
                if problems:
                    st.error(" / ".join(problems))
                elif new != ss.slots:
                    ss.undo.append(ss.slots)
                    ss.hist.insert(0, f"{s.id} 바꿈")
                    ss.slots = new
                    st.rerun()
        c1, c2, c3 = st.columns(3)
        if c1.button("＋ 칸 추가"):
            ss.undo.append(ss.slots)
            ss.slots = sl.add_slot(ss.slots)
            ss.sel = ss.slots[-1].id
            ss.hist.insert(0, f"{ss.sel} 추가")
            st.rerun()
        if c2.button("되돌리기", disabled=not ss.undo):
            ss.slots = ss.undo.pop()
            ss.hist.insert(0, "되돌림")
            st.rerun()
        sure = c3.checkbox("삭제 확인", key=f"del_ok_{s.id}")
        if st.button(f"{s.id} 칸 삭제", disabled=not sure):
            ss.undo.append(ss.slots)
            ss.slots = sl.delete(ss.slots, s.id)
            ss.hist.insert(0, f"{s.id} 삭제")
            st.rerun()
        if st.button("slots.yaml 로 저장", type="primary", disabled=bool(errs)):
            path = sl.save(ss.slots, SLOTS_PATH)
            records.append("map", "common", map_snapshot(), tag="slots.yaml 저장", log_dir=LOG_DIR)
            st.success(f"저장됨 → {path.relative_to(ROOT)}  (팀 합의 후 config/slots.yaml 로)")
        if ss.hist:
            st.caption("변경 기록: " + " · ".join(ss.hist[:8]))

    with st.expander("칸 목록 표"):
        st.dataframe(
            pd.DataFrame(
                [
                    {**x.to_dict(), "닿는 팔": ", ".join(sl.reach_by(x, ss.reach, ss.robots))}
                    for x in ss.slots
                ]
            ),
            hide_index=True,
        )
    w.save_bar("map", "작업대 지도", "칸 위치 · 이름 · 종류 편집", map_snapshot(), task_id="common")


def map_snapshot() -> dict:
    ss = st.session_state
    return {
        "table_mm": list(sl.TABLE_MM),
        "robots_mm": {k: list(v) for k, v in ss.robots.items()},
        "reach_mm": ss.reach,
        "slots": [x.to_dict() for x in ss.slots],
    }


def common_page() -> None:
    ss = st.session_state
    st.header("0 · 공통 설정")
    st.caption(
        "모든 작업이 같이 쓰는 것. 작업대와 카메라는 실제로 하나라 여기 한 곳에서만 바꿉니다."
    )
    cols = st.columns(len(COMMON))
    for i, (c, (k, n)) in enumerate(zip(cols, COMMON, strict=False), 1):
        if c.button(
            f"0-{i} {n}",
            key=f"c_{k}",
            type="primary" if ss.item == k else "secondary",
            width="stretch",
        ):
            nav(item=k)
    if ss.item == "map":
        map_page()
    elif ss.item:
        n = dict(COMMON)[ss.item]
        st.subheader(n)
        m = page_module("pages_common")
        if m is None:
            not_merged("pages_common")
        else:
            m.PAGES[ss.item]()


def main() -> None:
    st.set_page_config(page_title="Thursday 한방", layout="wide")
    init_state()
    sidebar()
    crumbs()
    sec = st.session_state.sec
    if sec == "task":
        task_page()
    elif sec == "common":
        common_page()
    else:
        home()


main()
