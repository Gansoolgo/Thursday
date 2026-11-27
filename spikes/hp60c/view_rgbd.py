"""HP60C 컬러 + 깊이를 한 창에 나란히 보기 (Windows).

먼저 다른 창에서 build\\hp60c_bridge.exe 를 실행해 둘 것.
마우스를 올린 곳의 거리(mm), 화면 가운데 거리, fps 를 표시한다.
종료: q / ESC / 창 X 버튼.   s: 컬러·깊이 저장 (snapshots/)
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from hp60c_reader import CameraReader

WIN = "HP60C RGB | Depth (q/ESC: quit)"
NEAR, FAR = 200, 2000  # 색 입힐 거리 범위 mm
mouse = (-1, -1)


def on_mouse(event, x, y, *_):
    global mouse
    if event == cv2.EVENT_MOUSEMOVE:
        mouse = (x, y)


def colorize(depth):
    d = np.clip((depth.astype(np.float32) - NEAR) / (FAR - NEAR), 0, 1)
    c = cv2.applyColorMap((d * 255).astype(np.uint8), cv2.COLORMAP_JET)
    c[depth == 0] = 0  # 0 = 깊이 없음 (검정)
    return c


def main():
    flip = "--flip" in sys.argv
    with CameraReader(wait_timeout=10) as cam:
        rgb, depth, fid = cam.read_blocking(timeout=5)
        if depth is None:
            print("깊이 프레임이 없습니다. bridge 창 메시지를 확인하세요.")
            return 1
        print(f"OK  RGB {None if rgb is None else rgb.shape}  Depth {depth.shape}")
        cv2.namedWindow(WIN)
        cv2.setMouseCallback(WIN, on_mouse)
        Path("snapshots").mkdir(exist_ok=True)
        last, fps, t_prev = fid, 0.0, time.monotonic()
        while True:
            r, d, f = cam.read_blocking(last, timeout=0.2)
            # 1초 넘게 새 프레임이 없으면 끊긴 것: 이전 값을 현재 측정값처럼 보이지 않게 (Codex 리뷰 11/27)
            stale = time.monotonic() - t_prev > 1.0
            if d is not None:
                rgb, depth, last = (r if r is not None else rgb), d, f
                now = time.monotonic()
                fps = (
                    0.9 * fps + 0.1 / max(now - t_prev, 1e-6)
                    if fps
                    else 1 / max(now - t_prev, 1e-6)
                )
                t_prev = now
            if flip:
                rgb_v, depth_v = cv2.rotate(rgb, cv2.ROTATE_180), cv2.rotate(depth, cv2.ROTATE_180)
            else:
                rgb_v, depth_v = rgb, depth
            dvis = colorize(depth_v)
            h, w = depth_v.shape
            left = (
                cv2.resize(rgb_v, (w, h))
                if rgb_v is not None and rgb_v.shape[:2] != (h, w)
                else rgb_v
            )
            if left is None:
                left = np.zeros_like(dvis)
            both = np.hstack([left, dvis])

            cx, cy = w // 2, h // 2
            if stale:
                both = (both * 0.4).astype(np.uint8)  # 어둡게
                lines = [
                    f"NO SIGNAL {time.monotonic() - t_prev:.0f}s - bridge/camera?",
                    "values hidden (last frame is old)",
                ]
                cv2.rectangle(both, (0, 0), (both.shape[1] - 1, both.shape[0] - 1), (0, 0, 255), 6)
            else:
                lines = [
                    f"{fps:4.1f} fps  frame {last}",
                    f"center: {int(depth_v[cy, cx])} mm",
                    f"valid depth: {(depth_v > 0).mean() * 100:4.1f}%",
                ]
            mx, my = mouse
            lx = mx - w if mx >= w else mx
            if not stale and 0 <= lx < w and 0 <= my < h:
                lines.append(f"mouse: {int(depth_v[my, lx])} mm")
                for xo in (lx, lx + w):
                    cv2.drawMarker(both, (xo, my), (255, 255, 255), cv2.MARKER_CROSS, 14, 1)
            for xo in (cx, cx + w):
                cv2.drawMarker(both, (xo, cy), (0, 255, 0), cv2.MARKER_CROSS, 18, 1)
            for i, t in enumerate(lines):
                cv2.putText(both, t, (10, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                cv2.putText(
                    both, t, (10, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1
                )

            cv2.imshow(WIN, both)
            k = cv2.waitKey(1) & 0xFF
            if (
                k in (ord("q"), ord("Q"), 27)
                or cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1
            ):
                break
            if k in (ord("s"), ord("S")):
                ts = time.strftime("%H%M%S")
                cv2.imwrite(f"snapshots/rgb_{ts}.png", rgb_v)
                cv2.imwrite(f"snapshots/depth_{ts}.png", depth_v)  # 16비트 PNG, 값 = mm
                print("저장:", ts)
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
