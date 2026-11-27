"""Thursday 한방 — 작업대 지도 (Issue #46).

칸(Slot) 목록을 만들고 고치는 함수 모음입니다. 화면(hanbang.py)은 이 함수만 부릅니다.

작업대 (사용자 지정, 2026-11-27)
- 가로(좌우) 60 cm × 세로(앞뒤) 45 cm. 사람은 앞쪽, 로봇팔 A · B 는 건너편(뒤쪽) 모서리 쪽.
- 원점 = 커팅 매트 모서리의 ArUco 마커 (D-16, interfaces.md 0장). 어느 모서리 · 어느 축인지는
  #5 보정 때 정하므로, 그때까지 임시로: 원점 = 뒤쪽(로봇 쪽) 모서리 중 사람이 볼 때 왼쪽(로봇 A 쪽),
  x = 사람 쪽(앞, 0~450), y = 사람이 볼 때 오른쪽(0~600), z = 위. 오른손 좌표계.
  #5 에서 정해지면 이 값만 바꾸면 됨.
- 로봇 받침 위치(ROBOTS)와 닿는 범위는 실측 전 예시 숫자. 화면에서 바꿀 수 있다.

약속
- 단위 mm — interfaces.md 0장
- **ID 는 고정**, 사람이 보는 이름(name)만 바꾼다. 프로그램·기록이 ID 로 칸을 찾기 때문.
- 함수는 원본 목록을 바꾸지 않고 **새 목록을 돌려준다** (되돌리기를 쉽게 하려고).
- zone 값은 interfaces.md 2장 (storage · work · assembly · handover).
  반납 칸 R 과 건넴 구역은 2장에 값이 없어 임시로 return · handover_zone 을 쓴다
  (interfaces 9장 질문으로 올림).
- v0 은 config/slots.yaml(공통 파일)을 건드리지 않고 logs/hanbang/slots.yaml 에 저장한다.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path

ZONES = {
    "storage": "보관",
    "work": "작업 (트레이 자리)",
    "assembly": "조립 줄",
    "handover": "전달",
    "return": "반납 (임시 값)",
    "handover_zone": "건넴 구역 (임시 값)",
}
_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,15}$")
DEFAULT_PATH = Path("logs/hanbang/slots.yaml")
TABLE_MM = (450.0, 600.0)  # (앞뒤 x, 좌우 y) — 세로 45 cm · 가로 60 cm
# 로봇 받침 중심 (x, y) mm. A = 사람이 볼 때 왼쪽 뒤, B = 오른쪽 뒤 (배치도 기준, 실측 전)
ROBOTS: dict[str, tuple[float, float]] = {"A": (0.0, 150.0), "B": (0.0, 450.0)}


@dataclass(frozen=True)
class Slot:
    id: str
    name: str
    zone: str
    center_mm: tuple[float, float, float]
    size_mm: tuple[float, float]  # (앞뒤 x 길이, 좌우 y 길이)
    home: str | None = None  # 제자리 물건 (objects.yaml 키)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["center_mm"] = list(self.center_mm)
        d["size_mm"] = list(self.size_mm)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Slot:
        c = d.get("center_mm", (0, 0, 0))
        s = d.get("size_mm", (40, 40))
        return cls(
            id=str(d["id"]),
            name=str(d.get("name") or ""),
            zone=str(d.get("zone", "storage")),
            center_mm=(float(c[0]), float(c[1]), float(c[2])),
            size_mm=(float(s[0]), float(s[1])),
            home=d.get("home") or None,
        )


def default_slots() -> list[Slot]:
    """60 × 45 cm 작업대 배치도(보관·정리대 = 사람이 볼 때 오른쪽)를 가정한 시작 값.

    실측 전 예시 숫자. 사람 쪽 끝(앞 10 cm 쯤)은 두 팔 모두 닿기 어려워 비워 둠.
    """
    out: list[Slot] = []
    names = {
        "S1": ("파랑 블록", "block_blue"),
        "S2": ("노랑 블록", "block_yellow"),
        "S3": ("저항 케이스", "resistor_case"),
    }
    n = 1
    for x in (100.0, 145.0, 190.0):  # 보관·정리대: 뒤 → 앞
        for y in (575.0, 535.0, 495.0):  # 사람이 볼 때 오른쪽 끝부터
            sid = f"S{n}"
            name, home = names.get(sid, ("", None))
            out.append(Slot(sid, name, "storage", (x, y, 0.0), (40.0, 40.0), home))
            n += 1
    out.append(Slot("T", "트레이 자리", "work", (150.0, 340.0, 0.0), (70.0, 90.0), "block_tray"))
    for i in range(1, 7):  # 조립 줄: A1 이 사람에게 가장 가까움
        out.append(
            Slot(f"A{i}", f"조립 줄 {i}", "assembly", (302.0 - i * 22, 260.0, 0.0), (20.0, 36.0))
        )
    out.append(Slot("Z", "건넴 구역", "handover_zone", (320.0, 110.0, 0.0), (120.0, 140.0)))
    out.append(Slot("H", "전달", "handover", (290.0, 100.0, 0.0), (44.0, 44.0)))
    out.append(Slot("R", "반납", "return", (290.0, 420.0, 0.0), (40.0, 40.0)))
    return out


def get(slots: list[Slot], slot_id: str) -> Slot:
    for s in slots:
        if s.id == slot_id:
            return s
    raise KeyError(f"없는 칸: {slot_id}")


def update(slots: list[Slot], slot_id: str, **fields) -> list[Slot]:
    """칸 하나의 값을 바꾼 새 목록. ID 는 바꿀 수 없다."""
    if "id" in fields and fields["id"] != slot_id:
        raise ValueError("칸 ID 는 바꿀 수 없습니다 (이름만 바꾸세요)")
    get(slots, slot_id)  # 없으면 KeyError
    return [replace(s, **fields) if s.id == slot_id else s for s in slots]


def rename(slots: list[Slot], slot_id: str, name: str) -> list[Slot]:
    return update(slots, slot_id, name=name.strip())


def move(slots: list[Slot], slot_id: str, x: float, y: float) -> list[Slot]:
    z = get(slots, slot_id).center_mm[2]
    return update(slots, slot_id, center_mm=(float(x), float(y), z))


def add_slot(slots: list[Slot], prefix: str = "S") -> list[Slot]:
    """겹치지 않는 다음 번호로 보관 칸 하나 추가."""
    used = {s.id for s in slots}
    n = 1
    while f"{prefix}{n}" in used:
        n += 1
    return slots + [Slot(f"{prefix}{n}", "", "storage", (150.0, 300.0, 0.0), (40.0, 40.0))]


def delete(slots: list[Slot], slot_id: str) -> list[Slot]:
    get(slots, slot_id)
    return [s for s in slots if s.id != slot_id]


def _corners(slot: Slot) -> list[tuple[float, float]]:
    x, y, _ = slot.center_mm
    dx, dy = slot.size_mm[0] / 2, slot.size_mm[1] / 2
    return [(x + sx * dx, y + sy * dy) for sx in (-1, 1) for sy in (-1, 1)]


def reach_by(slot: Slot, radius_mm: float, robots: dict | None = None) -> list[str]:
    """이 칸의 네 모서리에 모두 닿는 로봇 이름 목록 (예: ["B"])."""
    robots = ROBOTS if robots is None else robots
    return [
        name
        for name, (rx, ry) in robots.items()
        if all(math.hypot(cx - rx, cy - ry) <= radius_mm for cx, cy in _corners(slot))
    ]


def in_reach(slot: Slot, radius_mm: float, robots: dict | None = None) -> bool:
    """로봇 중 하나라도 칸 전체에 닿는가. 건넴 구역(넓은 영역)은 검사하지 않는다."""
    if slot.zone == "handover_zone":
        return True
    return bool(reach_by(slot, radius_mm, robots))


def outside_table(slots: list[Slot], table_mm: tuple[float, float] = TABLE_MM) -> list[str]:
    """작업대(앞뒤 0~table_mm[0], 좌우 0~table_mm[1]) 밖으로 나간 칸 ID 목록."""
    depth, width = table_mm
    return [
        s.id
        for s in slots
        if any(not (0 <= cx <= depth and 0 <= cy <= width) for cx, cy in _corners(s))
    ]


def validate(slots: list[Slot]) -> list[str]:
    """문제 목록 (없으면 빈 목록)."""
    errs: list[str] = []
    seen: set[str] = set()
    for s in slots:
        if not _ID_RE.match(s.id):
            errs.append(f"{s.id}: ID 는 영문자로 시작, 영문·숫자·_ 16자 이하")
        if s.id in seen:
            errs.append(f"{s.id}: ID 가 겹칩니다")
        seen.add(s.id)
        if s.size_mm[0] <= 0 or s.size_mm[1] <= 0:
            errs.append(f"{s.id}: 크기는 0 보다 커야 합니다")
        if s.zone not in ZONES:
            errs.append(f"{s.id}: 모르는 종류(zone) {s.zone!r}")
    return errs


def save(slots: list[Slot], path: str | Path = DEFAULT_PATH) -> Path:
    """interfaces.md 2장 slots.yaml 모양 (ID → 값) 으로 저장."""
    import yaml  # 저장·불러오기 때만 필요 (CI 는 requirements-dev 만 설치하므로 여기서 불러옴)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    for s in slots:
        d = s.to_dict()
        d.pop("id")
        data[s.id] = d
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def load(path: str | Path = DEFAULT_PATH) -> list[Slot]:
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [Slot.from_dict({"id": k, **(v or {})}) for k, v in data.items()]
