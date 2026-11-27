# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""5 기록·결과 — 5-1 사용 기록 · 5-2 시험 기록 · 정답 · 5-3 비교 모드 · 5-4 결과 요약 (발표 표)."""

from __future__ import annotations

import csv
import io
import random

import streamlit as st

from app.ui import logic as lg
from app.ui import widgets as w

SCRIPT = {
    "block_a": [
        "A1 에 파랑 놓기 → 로봇이 노랑을 미리 집음",
        "A2 에 일부러 주황 → 로봇이 묻기",
        "H 의 블록 가져가기 → 다음 블록 준비",
        "R 에 블록 놓기 → 수시 정리",
        '트레이에서 초록 숨기기 → "초록이 없어요" 알림',
        "자리 떠나기 → 남은 물건 정리",
    ],
    "fold_cloth": [
        "모서리 1개 접어 놓기 → 펴기 1번 고름",
        "펴진 채 놓기 → 바로 접기",
        '구긴 채 놓기 → "펴 주세요"',
    ],
    "safety": ["이동 중 손 넣기 → 정지", "건넴 구역 밖 손 → 계속", "정지 버튼 → 즉시 정지"],
}
EVENTS = {"prepared": "꺼내 둠", "handed_over": "건넴", "returned": "정리함"}


def usage() -> None:
    d = w.td()
    st.caption(
        "무엇을 언제 꺼내고 건네고 정리했는지 남깁니다 (interfaces.md 6장 usage.jsonl). 많이 쓴 물건은 4-3 정리에서 가까운 칸으로 갑니다."
    )
    objs = d["manual"]["objects"] or ["object_1"]
    c1, *cols = st.columns([2, 1, 1, 1])
    obj = c1.selectbox("물건", objs)
    for col, (ev, label) in zip(cols, EVENTS.items(), strict=True):
        if col.button(label, key=f"ev_{ev}"):
            d["usage"].append(
                {"t": w.now(), "사건": ev, "물건": obj, "작업": st.session_state.task}
            )
    cnt: dict[str, int] = {}
    for u in d["usage"]:
        if u["사건"] != "returned":
            cnt[u["물건"]] = cnt.get(u["물건"], 0) + 1
    if cnt:
        st.bar_chart(dict(sorted(cnt.items(), key=lambda x: -x[1])), horizontal=True)
    w.table(d["usage"][::-1][:15])
    w.save_bar("usage", "사용 기록", "사용 빈도 (정리 최적화 근거)", d["usage"])


def trial() -> None:
    d = w.td()
    t = d["trials"]
    ok = sum(x["res"] in ("SUCCESS", "DONE", "STOPPED", "IGNORED_OK") for x in t)
    m1, m2, m3 = st.columns(3)
    m1.metric("시험 횟수", len(t))
    m2.metric("성공률 (95% 범위)", lg.pct_ci(ok, len(t)))
    m3.metric("평균 시간", f"{sum(x['sec'] for x in t) / len(t):.1f}초" if t else "-")
    sc = SCRIPT.get(st.session_state.task, [])
    if sc:
        st.markdown(
            "**시험 대본 + 정답 버튼** — 대본대로 하고, 로봇이 맞게 반응했는지 눌러 정답을 남깁니다 (evaluation.md 4장)"
        )
        for i, s in enumerate(sc):
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.write(f"{i + 1}. {s}")
            if c2.button("✓", key=f"scr_ok_{i}"):
                w.add_trial(f"[대본] {s}", "SUCCESS", 0, "H4", truth=True)
            if c3.button("✗", key=f"scr_ng_{i}"):
                w.add_trial(f"[대본] {s}", "FAILED", 0, "H4", truth=True)
    w.table(t[::-1], "재생 · 시험 · 자율 모드를 하면 여기에 자동으로 쌓입니다.")
    w.save_bar("trial", "시험 기록", "성공률 · 정답", t, rows=[("성공률", lg.pct_ci(ok, len(t)))])


def _avg(rows: list[dict], key: str):
    return round(sum(x[key] for x in rows) / len(rows), 1) if rows else "-"


def compare() -> None:
    d = w.td()
    st.caption(
        "비교군 = 같은 로봇 · 같은 Skill · 같은 안전 검사를 쓰되, 정해진 명령어와 고정 순서로만 움직이는 로봇 (evaluation.md 2장). "
        "규칙 기반이 더 나은 지표(예: 반응 속도)도 그대로 보고합니다."
    )
    sysname = (
        st.segmented_control(
            "지금 시험하는 시스템",
            ["thursday", "rule_based"],
            default="thursday",
            format_func={"thursday": "Thursday", "rule_based": "규칙 기반"}.get,
            key="cmp_sys",
        )
        or "thursday"
    )
    if st.button("블록 작업 1회 (예시 값)", type="primary"):
        th = sysname == "thursday"
        d["cmp"].append(
            {
                "t": w.now(),
                "system": sysname,
                "완주": random.random() < (0.85 if th else 0.9),
                "명령 수": random.randint(1, 3) if th else random.randint(8, 12),
                "작업 초": random.randint(140, 190) if th else random.randint(170, 240),
                "말→움직임 초": round(
                    random.uniform(2.5, 4.2) if th else random.uniform(0.9, 1.5), 1
                ),
            }
        )
    rows = []
    for s, name in (("thursday", "Thursday"), ("rule_based", "규칙 기반")):
        a = [x for x in d["cmp"] if x["system"] == s]
        rows.append(
            {
                "시스템": name,
                "횟수": len(a),
                "완주율": lg.pct_ci(sum(x["완주"] for x in a), len(a)),
                "사람이 말한 명령 수": _avg(a, "명령 수"),
                "작업 초": _avg(a, "작업 초"),
                "말→움직임 초": _avg(a, "말→움직임 초"),
            }
        )
    w.table(rows)
    w.table(d["cmp"][::-1])
    w.save_bar("compare", "비교 모드", "Thursday vs 규칙 기반", d["cmp"])


def summary_rows() -> list[dict]:
    d, task = w.td(), st.session_state.task
    out = []

    def add(name, value, hyp, where):
        out.append({"지표": name, "값": value, "가설": hyp, "어디서": where})

    sk = [x for x in d["trials"] if not x.get("h")]
    add(
        "동작 · 재생 성공률",
        lg.pct_ci(sum(x["res"] in ("SUCCESS", "DONE") for x in sk), len(sk)),
        "신뢰성",
        "1-1 · 5-2",
    )
    g = d["gate_runs"][-1] if d["gate_runs"] else None
    add("위험 요청 거절", lg.pct_ci(g["blocked"], len(g["bad"])) if g else "측정 전", "H5", "3-3")
    add(
        "정상 요청 잘못 거절", f"{g['false_rej']} / {len(g['ok'])}" if g else "측정 전", "H5", "3-3"
    )
    add(
        "손 보이면 정지",
        lg.pct_ci(
            sum(x["결과"] in ("STOPPED", "IGNORED_OK") for x in d["safety"]), len(d["safety"])
        ),
        "H5",
        "3-4",
    )
    mj = [x for x in d["mic"] if x["ok"] is not None]
    add("음성 명령 정확도", lg.pct_ci(sum(x["ok"] for x in mj), len(mj)), "인식", "2-1")
    vd = [x for v in d["vis"] for x in v["dets"] if x["정답"] is not None]
    add("물체 인식 정답률", lg.pct_ci(sum(bool(x["정답"]) for x in vd), len(vd)), "인식", "2-2")
    p = d["prog"]
    add(
        "단계 추정 정확도",
        lg.pct_ci(sum(p["truth"]), len(p["truth"])) if p else "측정 전",
        "H4",
        "4-2",
    )
    add(
        "순서 이탈 감지",
        f"{sum(e['k'] == '이탈' for e in p['events'])}번" if p else "측정 전",
        "H4 · D-14",
        "4-2",
    )
    if task == "fold_cloth":
        add(
            "손수건 초기 상태 판단",
            lg.pct_ci(sum(x["맞음"] for x in d["cloth"]), len(d["cloth"])),
            "H4 · D-07",
            "2-4",
        )
    else:
        add(
            "손 위 전달 방식 선택",
            lg.pct_ci(sum(x["맞음"] for x in d["hand"]), len(d["hand"])),
            "H4 · D-08",
            "2-4",
        )
    lr = d["layout_runs"][-1] if d["layout_runs"] else None
    add(
        "정리 후 꺼내기 거리 감소",
        f"{round((1 - lr['fused'] / lr['fixed']) * 100)}% (시뮬레이션)"
        if lr and lr["fixed"]
        else "측정 전",
        "H3",
        "4-3",
    )
    v = d["manual"]["ver"][-1] if d["manual"]["ver"] else None
    add(
        "새 작업 추가 시간 · 엔진 수정",
        f"{v['작성 초'] // 60}분 {v['작성 초'] % 60}초 · 0줄" if v else "측정 전",
        "H1",
        "4-1",
    )
    lat = [e["total"] for s in d["sessions"] for e in s["events"] if e.get("total")]
    add(
        "말 끝 → 로봇 움직임",
        f"중앙값 {lg.median(lat) / 1000:.1f}초 · 95% {lg.p95(lat) / 1000:.1f}초 ({len(lat)}건)"
        if lat
        else "측정 전",
        "속도",
        "99",
    )
    add(
        "자율 모드 세션",
        f"{len(d['sessions'])}개 · 사건 {sum(len(s['events']) for s in d['sessions'])}건"
        if d["sessions"]
        else "측정 전",
        "시나리오",
        "99",
    )
    return out


def summary() -> None:
    rows = summary_rows()
    st.caption(
        "이 작업에서 모은 기록으로 자동 계산합니다. 성공률은 '90% (70~97%)'처럼 **95% 범위**로 씁니다 — 횟수가 적을 때 과장하지 않으려고. "
        "유리한 것만 고르지 않고 측정한 건 다 보여 줍니다. 숫자는 지금 Mock 이라 예시입니다."
    )
    w.table(rows)
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)
    st.download_button(
        "⤓ 표 내려받기 (CSV)",
        buf.getvalue().encode("utf-8-sig"),
        file_name=f"{st.session_state.task}_summary.csv",
        mime="text/csv",
    )
    w.save_bar(
        "summary",
        "결과 요약",
        "발표 표 (results-m1 재료)",
        rows,
        rows=[(r["지표"], r["값"]) for r in rows],
    )


PAGES = {"usage": usage, "trial": trial, "compare": compare, "summary": summary}
