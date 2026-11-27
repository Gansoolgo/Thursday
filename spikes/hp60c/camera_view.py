"""카메라 실제 화면을 보면서 설치 위치를 정하는 도우미 (OpenCV).

화면에 보이는 것
- 가운데 십자선, 3×3 격자 (카메라가 판 중심을 보는지)
- 해상도, fps
- 판 네 모서리를 마우스로 찍으면: 판이 화면에서 차지하는 비율, 가로 mm/픽셀,
  블록 40 mm가 몇 픽셀인지, 판이 화면 안에 다 들어왔는지

사용법 (PowerShell)
    python camera_view.py --list                 # 연결된 카메라 번호 찾기
    python camera_view.py --cam 1 --board 600x450  # 1번 카메라, 판 크기 600×450 mm

키
    q·ESC·창 X 버튼 끝내기 | n 다음 카메라 | g 격자 켜기/끄기 | c 찍은 점 지우기 | s 화면 저장(snapshots/)

참고
- HP60C는 Windows에서 컬러 영상이 일반 웹캠(UVC)처럼 잡힐 가능성이 높습니다(미확인).
  깊이 영상은 보통 제조사 SDK가 필요해서 이 스크립트로는 안 나올 수 있습니다.
- 노트북 내장 카메라(Integrated Camera)도 번호를 차지하니 --list로 먼저 확인하세요.
"""

import argparse
import os
import time
from pathlib import Path

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")  # 없는 번호를 열 때 경고 숨김

import cv2  # noqa: E402
import numpy as np  # noqa: E402

BLOCK_MM = 40
points: list[tuple[int, int]] = []


def open_cam(idx, w, h):
    # HP60C는 DSHOW로 열면 검은 화면(전부 0)이고 MSMF로 열어야 영상이 나옴 (11/27 확인)
    for backend in (cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY):
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            break
    else:
        return None
    if w and h:  # HP60C는 해상도를 지정하면 프레임이 안 나옴 → 기본값으로 둠
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    return cap


def list_cams(max_idx=8):
    print("번호 | 열림 | 해상도")
    for i in range(max_idx):
        cap = open_cam(i, 640, 480)
        if cap is None:
            continue
        ok, frame = cap.read()
        shape = f"{frame.shape[1]}×{frame.shape[0]}" if ok else "프레임 없음"
        print(f"  {i}  |  O  | {shape}")
        cap.release()


def on_mouse(event, x, y, *_):
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append((x, y))


def draw_overlay(frame, fps, show_grid, board_mm, cam_idx):
    h, w = frame.shape[:2]
    green, yellow, red = (0, 220, 0), (0, 220, 255), (0, 0, 255)
    cv2.line(frame, (w // 2 - 30, h // 2), (w // 2 + 30, h // 2), green, 1)
    cv2.line(frame, (w // 2, h // 2 - 30), (w // 2, h // 2 + 30), green, 1)
    if show_grid:
        for k in (1, 2):
            cv2.line(frame, (w * k // 3, 0), (w * k // 3, h), (180, 180, 180), 1)
            cv2.line(frame, (0, h * k // 3), (w, h * k // 3), (180, 180, 180), 1)

    # OpenCV 기본 글꼴은 한글을 못 그려서 화면 문구는 영어로 둔다
    lines = [f"cam {cam_idx}  {w}x{h}  {fps:4.1f} fps", "Click 4 board corners (c: clear)"]
    for p in points:
        cv2.circle(frame, p, 5, yellow, -1)
    if len(points) == 4:
        for i in range(4):
            cv2.line(frame, points[i], points[(i + 1) % 4], yellow, 2)
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        bw_px = max(xs) - min(xs)
        area = cv2.contourArea(np.array(points, dtype=np.float32))
        ratio = area / (w * h) * 100
        mm_px = board_mm[0] / bw_px if bw_px else 0
        block_px = BLOCK_MM / mm_px if mm_px else 0
        margin = min(min(xs), min(ys), w - max(xs), h - max(ys))
        inside = margin > 10
        lines = [
            lines[0],
            f"board covers {ratio:4.1f}% of frame",
            f"{mm_px:4.2f} mm/px -> 40mm block = {block_px:3.0f}px",
            f"edge margin {margin}px " + ("OK" if inside else "BOARD OUT OF FRAME!"),
        ]
        if not inside:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), red, 4)

    y = 22
    for t in lines:
        cv2.putText(frame, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(frame, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        y += 22
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--board", default="600x450", help="판 크기 mm, 예: 600x450 (A2), 900x600 (A1)")
    ap.add_argument(
        "--size",
        default="",
        help="요청 해상도 예: 1280x720 (비우면 카메라 기본값, HP60C는 비워 둘 것)",
    )
    ap.add_argument(
        "--flip", action="store_true", help="화면 180도 돌리기 (카메라를 거꾸로 달았을 때)"
    )
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        list_cams()
        return

    board_mm = tuple(int(v) for v in a.board.lower().split("x"))
    rw, rh = (int(v) for v in a.size.lower().split("x")) if a.size else (0, 0)
    cam_idx = a.cam
    cap = open_cam(cam_idx, rw, rh)
    if cap is None:
        print(f"{cam_idx}번 카메라를 열 수 없습니다. --list로 번호를 확인하세요.")
        return

    win = "camera_view (q/ESC: quit)"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)
    show_grid, t0, n, fps, fails = True, time.time(), 0, 0.0, 0
    Path("snapshots").mkdir(exist_ok=True)

    while True:
        ok, frame = cap.read()
        if not ok:
            fails += 1
            if fails > 100:  # 켜진 직전 몇 프레임은 실패할 수 있어 기다림
                print("frame read failed (camera busy or unsupported)")
                break
            if cv2.waitKey(30) & 0xFF == ord("q"):  # 실패 중에도 창이 멈추지 않게
                break
            continue
        fails = 0
        n += 1
        if time.time() - t0 >= 1:
            fps, t0, n = n / (time.time() - t0), time.time(), 0
        if a.flip:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        raw = frame.copy()
        cv2.imshow(win, draw_overlay(frame, fps, show_grid, board_mm, cam_idx))
        key = cv2.waitKey(1) & 0xFF
        # q, Q, ESC, 또는 창의 X 버튼으로 종료 (한글 입력 상태에서는 q가 안 먹을 수 있어 ESC도 받음)
        if key in (ord("q"), ord("Q"), 27) or cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
            break
        if key == ord("g"):
            show_grid = not show_grid
        if key == ord("c"):
            points.clear()
        if key == ord("s"):
            name = f"snapshots/cam{cam_idx}_{time.strftime('%H%M%S')}.png"
            cv2.imwrite(name, raw)
            print("저장:", name)
        if key == ord("n"):
            cap.release()
            nxt = None
            for _ in range(8):  # 다음으로 열리는 카메라 찾기
                cam_idx = (cam_idx + 1) % 8
                nxt = open_cam(cam_idx, rw, rh)
                if nxt is not None:
                    break
            if nxt is None:
                print("열 수 있는 카메라가 없습니다.")
                break
            cap = nxt
            points.clear()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
