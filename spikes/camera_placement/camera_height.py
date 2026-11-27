"""HP60C 상부 카메라 설치 높이 시뮬레이션 (핀홀 카메라 모델, 표준 라이브러리만 사용).

가정 (판매처 발표값·추정값, 실측 아님):
- 시야각: 수평 73.8°, 수직 58.8°
- 깊이 최소 거리 0.2 m (그보다 가까우면 깊이 없음)
- 깊이 영상 해상도 640×480 (공식 값 미확인)
- 깊이 오차는 거리 제곱에 비례 (구조광 일반 특성). 0.5 m에서 σ = 2 mm 로 가정
- 손 위 전달 때 손 높이: 작업대 위 최대 25 cm
- SO-101 팔 최고 높이: 작업대 위 약 40 cm (미측정)

실행: python camera_height.py  → 표 출력 + camera_height.svg 생성
"""

import math
from pathlib import Path

HFOV, VFOV = 73.8, 58.8
MIN_RANGE_CM = 20.0
RES_W, RES_H = 640, 480
SIGMA_AT_50CM_MM = 2.0
HAND_MAX_CM = 25.0
ARM_TOP_CM = 40.0
MARGIN = 1.10  # 가장자리 왜곡·설치 오차 여유 10%

BOARDS = {"A2 (60×45 cm)": (60.0, 45.0), "A1 (90×60 cm)": (90.0, 60.0)}


def footprint(h_cm):
    """높이 h에서 바로 아래를 볼 때 작업대 위 시야 크기 (가로, 세로) cm."""
    return (
        2 * h_cm * math.tan(math.radians(HFOV / 2)),
        2 * h_cm * math.tan(math.radians(VFOV / 2)),
    )


def min_height(w_cm, d_cm):
    """판 전체가 여유 포함 시야에 들어오는 최소 높이. 긴 변을 카메라 가로에 맞춤."""
    hw = (w_cm * MARGIN / 2) / math.tan(math.radians(HFOV / 2))
    hd = (d_cm * MARGIN / 2) / math.tan(math.radians(VFOV / 2))
    return max(hw, hd)


def row(h):
    fw, fd = footprint(h)
    mm_px = fw * 10 / RES_W
    block_px = 40 / mm_px
    sigma = SIGMA_AT_50CM_MM * (h / 50) ** 2
    hand_dist = h - HAND_MAX_CM
    ok_hand = hand_dist >= MIN_RANGE_CM
    ok_arm = h >= ARM_TOP_CM + 10
    return fw, fd, mm_px, block_px, sigma, hand_dist, ok_hand, ok_arm


def table():
    print("== 판 전체가 들어오는 최소 높이 (여유 10%) ==")
    for name, (w, d) in BOARDS.items():
        print(f"  {name}: {min_height(w, d):.0f} cm")
    print()
    print("== 높이별 결과 ==")
    print(
        " 높이 | 시야(가로×세로) | mm/픽셀 | 블록 40mm 픽셀 | 깊이 오차σ | 손(25cm)까지 | 손 OK | 팔과 10cm 여유"
    )
    for h in range(40, 101, 10):
        fw, fd, mm_px, bpx, sig, hd, okh, oka = row(h)
        print(
            f" {h:3d}cm | {fw:5.0f}×{fd:3.0f} cm   | {mm_px:5.2f}  | {bpx:6.0f}         | {sig:4.1f} mm   "
            f"| {hd:4.0f} cm      | {'O' if okh else 'X'}    | {'O' if oka else 'X'}"
        )


def svg(path):
    """옆에서 본 그림: 높이 50·65·80 cm의 시야(세로 방향)와 사각지대."""
    W, H, S = 900, 520, 5.0  # 1 cm = 5 px
    ox, oy = 450, 470  # 작업대 중심, 표면
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="13">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="20" y="28" font-size="16" font-weight="700">상부 카메라 높이별 시야 (옆에서 본 그림, 가로 방향 73.8° 기준)</text>',
    ]
    # 작업대 A2 / A1
    for w, col, lab in [(90, "#d0d7de", "A1 90cm"), (60, "#8c959f", "A2 60cm")]:
        parts.append(
            f'<rect x="{ox - w / 2 * S}" y="{oy}" width="{w * S}" height="10" fill="{col}"/>'
        )
        parts.append(
            f'<text x="{ox + w / 2 * S + 6}" y="{oy + 10 + (12 if w == 90 else 0)}" fill="#57606a">{lab}</text>'
        )
    # 팔 높이, 손 높이
    for hcm, col, lab in [
        (ARM_TOP_CM, "#cf222e", f"팔 최고 높이(가정) {ARM_TOP_CM:.0f}cm"),
        (HAND_MAX_CM, "#bf8700", f"손 최대 높이(가정) {HAND_MAX_CM:.0f}cm"),
    ]:
        y = oy - hcm * S
        parts.append(
            f'<line x1="60" y1="{y}" x2="840" y2="{y}" stroke="{col}" stroke-dasharray="6 4"/>'
        )
        parts.append(f'<text x="64" y="{y - 4}" fill="{col}">{lab}</text>')
    colors = {50: "#0969da", 65: "#1a7f37", 80: "#8250df"}
    for h, col in colors.items():
        cy = oy - h * S
        half = h * math.tan(math.radians(HFOV / 2))
        parts.append(
            f'<polygon points="{ox},{cy} {ox - half * S},{oy} {ox + half * S},{oy}" fill="{col}" fill-opacity="0.07" stroke="{col}"/>'
        )
        # 사각지대 20 cm
        r = MIN_RANGE_CM
        bh = r * math.tan(math.radians(HFOV / 2))
        parts.append(
            f'<polygon points="{ox},{cy} {ox - bh * S},{cy + r * S} {ox + bh * S},{cy + r * S}" fill="#000" fill-opacity="0.18"/>'
        )
        parts.append(f'<circle cx="{ox}" cy="{cy}" r="6" fill="{col}"/>')
        parts.append(
            f'<text x="{ox + 12}" y="{cy + 4}" fill="{col}" font-weight="700">{h} cm (시야 {2 * half:.0f} cm)</text>'
        )
    parts.append(
        '<text x="20" y="508" fill="#57606a">회색 삼각형 = 깊이가 안 나오는 0.2 m 사각지대. 손·팔이 여기에 들어오면 깊이 값이 없음. 수치는 판매처 사양과 가정값 기준.</text>'
    )
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    table()
    out = Path(__file__).with_name("camera_height.svg")
    svg(out)
    print(f"\n그림: {out}")
