"""작업대 지도(slots) 테스트 — Issue #46 완료 조건 3~7."""

import pytest

from app.ui import slots as sl


def test_rename_changes_only_name_and_keeps_id():
    before = sl.default_slots()
    after = sl.rename(before, "S3", "공구함")
    s3 = sl.get(after, "S3")
    assert s3.id == "S3"
    assert s3.name == "공구함"
    assert sl.get(before, "S3").name != "공구함"  # 원본 목록은 바뀌지 않음


def test_rename_unknown_id_raises():
    with pytest.raises(KeyError):
        sl.rename(sl.default_slots(), "Q9", "없는 칸")


def test_add_slot_gives_next_free_id():
    one = sl.add_slot(sl.default_slots())
    assert one[-1].id == "S10"
    two = sl.add_slot(one)
    assert two[-1].id == "S11"


def test_delete_removes_one():
    base = sl.default_slots()
    out = sl.delete(base, "S9")
    assert len(out) == len(base) - 1
    with pytest.raises(KeyError):
        sl.get(out, "S9")


def test_update_changes_fields_but_not_id():
    out = sl.update(sl.default_slots(), "H", center_mm=(225.0, -150.0, 0.0), home="block_blue")
    h = sl.get(out, "H")
    assert h.center_mm == (225.0, -150.0, 0.0)
    assert h.home == "block_blue"
    with pytest.raises(ValueError):
        sl.update(out, "H", id="H2")


def test_default_layout_is_inside_reach():
    far = [s.id for s in sl.default_slots() if not sl.in_reach(s, 330)]
    assert far == []


def test_slot_moved_far_forward_is_out_of_reach():
    moved = sl.move(sl.default_slots(), "S1", x=440, y=0)  # 사람 쪽 끝 가운데: 두 팔 모두 멀다
    assert not sl.in_reach(sl.get(moved, "S1"), 330)


def test_table_is_60_by_45_cm():
    # 사용자 지정: 가로(좌우) 60 cm · 세로(앞뒤) 45 cm → size = (앞뒤 x, 좌우 y)
    assert sl.TABLE_MM == (450.0, 600.0)


def test_default_layout_is_on_the_table_and_off_table_is_found():
    assert sl.outside_table(sl.default_slots()) == []
    moved = sl.move(sl.default_slots(), "S2", x=470, y=0)
    assert sl.outside_table(moved) == ["S2"]


def test_reach_by_names_which_arm_reaches():
    # 로봇 A = 사람 쪽에서 볼 때 왼쪽 뒤 (y 음수), B = 오른쪽 뒤 (y 양수)
    near_b = sl.Slot("Q1", "", "storage", (120.0, 250.0, 0.0), (40.0, 40.0))
    assert sl.reach_by(near_b, 330) == ["B"]
    middle = sl.Slot("Q2", "", "storage", (150.0, 0.0, 0.0), (40.0, 40.0))
    assert sl.reach_by(middle, 330) == ["A", "B"]


def test_validate_finds_problems():
    good = sl.default_slots()
    assert sl.validate(good) == []

    dup = good + [sl.Slot(id="S1", name="", zone="storage", center_mm=(0, 0, 0), size_mm=(40, 40))]
    assert any("S1" in e for e in sl.validate(dup))

    zero = sl.update(good, "S2", size_mm=(0.0, 40.0))
    assert any("S2" in e for e in sl.validate(zero))

    bad_id = good + [
        sl.Slot(id="S 3", name="", zone="storage", center_mm=(0, 0, 0), size_mm=(40, 40))
    ]
    assert any("S 3" in e for e in sl.validate(bad_id))

    bad_zone = sl.update(good, "S4", zone="kitchen")
    assert any("S4" in e for e in sl.validate(bad_zone))


def test_save_then_load_gives_same_slots(tmp_path):
    pytest.importorskip("yaml")  # CI(requirements-dev 만 설치)에서는 건너뜀 — 로컬 .venv 에서 확인
    path = tmp_path / "hanbang" / "slots.yaml"
    sl.save(sl.rename(sl.default_slots(), "S3", "저항 케이스"), path)
    assert sl.load(path) == sl.rename(sl.default_slots(), "S3", "저항 케이스")


def test_to_dict_from_dict_round_trip():
    s = sl.get(sl.default_slots(), "T")
    assert sl.Slot.from_dict(s.to_dict()) == s
