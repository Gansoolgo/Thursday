"""측면 HP60C 위치 시뮬레이션 (핀홀 모델, 표준 라이브러리만).

배치(가정): 측면 카메라는 판의 왼쪽 짧은 변 바깥에 있고, 판의 긴 변(가로) 방향을 비스듬히 내려다본다.
판 중심을 겨냥한다고 보고, 카메라의 수평 거리 d(판 가장자리에서 밖으로)와 높이 h를 바꿔 가며 검사한다.

검사 항목
1. 판 가까운 끝·먼 끝이 수직 시야(±29.4°) 안에 들어오는가
2. 판 가까운 끝에서 판 폭(깊이 방향)이 수평 시야 안에 다 들어오는가
3. 가장 가까운 점이 깊이 사각지대(20 cm)보다 먼가
4. 판 위 높이 Z cm 물체(손·팔)가 화면 위쪽으로 잘리지 않는가 (판 중심 기준)
5. 가장 먼 점 거리 (2 m 이내가 좋음, 가까울수록 정밀)
6. 내려다보는 각도 (얕을수록 높이·옆모습을 잘 봄, 깊을수록 가림이 적음)

실행: python side_camera.py
"""

import math

HFOV, VFOV = 73.8, 58.8
MIN_RANGE = 20.0
SEE_HEIGHT = 30.0  # 판 위 이 높이까지는 화면에 들어와야 함 (손 25 cm + 여유)
BOARDS = {"A1": (90.0, 60.0), "A2": (60.0, 45.0)}  # (카메라 시선 방향 길이, 폭)


def check(L, W, d, h):
    """L: 시선 방향 판 길이, W: 판 폭, d: 판 가장자리에서 카메라까지 수평 거리, h: 높이."""
    near_x, far_x, cx = d, d + L, d + L / 2
    pitch = math.degrees(math.atan2(h, cx))  # 판 중심을 겨냥할 때 내려다보는 각
    ang = lambda x, z=0.0: math.degrees(math.atan2(h - z, x)) - pitch  # 광축 기준 아래(+)
    a_near, a_far = ang(near_x), ang(far_x)
    a_top = ang(cx, SEE_HEIGHT)  # 판 중심 위 30 cm 점
    half_v = VFOV / 2
    ok_v = a_near <= half_v and a_far >= -half_v and a_top >= -half_v
    near_dist = math.hypot(near_x, h)
    # 시야 폭은 직선거리가 아니라 광축 방향 거리(깊이)로 계산해야 함 (Codex 리뷰 11/27)
    p_rad = math.radians(pitch)
    near_depth = near_x * math.cos(p_rad) + h * math.sin(p_rad)
    width_at_near = 2 * near_depth * math.tan(math.radians(HFOV / 2))
    far_dist = math.hypot(far_x, h)
    ok = ok_v and width_at_near >= W and near_dist >= MIN_RANGE + 5 and far_dist <= 200
    return ok, pitch, near_dist, far_dist, width_at_near, a_near, a_far, a_top


def main():
    for name, (L, W) in BOARDS.items():
        print(f"\n=== 판 {name} ({L:.0f}×{W:.0f} cm), 왼쪽 짧은 변 바깥에서 긴 변 방향으로 봄 ===")
        print(
            " 높이 | 판에서 떨어진 거리 | 내려다보는 각 | 가까운 점 | 먼 점 | 가까운 끝 시야폭 | 판정"
        )
        for h in (30, 40, 50, 60, 70):
            for d in (10, 20, 30, 40, 50):
                ok, p, nd, fd, wn, an, af, at = check(L, W, d, h)
                if ok:
                    print(
                        f" {h:3d}cm | {d:3d}cm             | {p:4.0f}°         | {nd:4.0f}cm   | {fd:4.0f}cm | {wn:4.0f}cm          | OK"
                    )
        print(" (OK인 조합만 표시)")


if __name__ == "__main__":
    main()
