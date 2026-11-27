"""HP60C 공유 메모리 reader (Windows).

hp60c_bridge.exe 가 쓰는 "Local\\hp60c_frames" 를 열어 RGB(BGR uint8)와 Depth(uint16 mm)를 numpy 로 돌려준다.
메모리 레이아웃은 th2102da/hp60c-camera 의 Linux 판과 같다.

    from hp60c_reader import CameraReader
    with CameraReader() as cam:
        rgb, depth, fid = cam.read_blocking()
"""

from __future__ import annotations

import mmap
import struct
import time

import numpy as np

SHM_NAME = "Local\\hp60c_frames"
SHM_MAGIC = 0x48503630
HEADER_SIZE = 64
MAX_RGB_SIZE = 1920 * 1080 * 3
MAX_DEPTH_SIZE = 640 * 480 * 2
SHM_TOTAL = HEADER_SIZE + MAX_RGB_SIZE + MAX_DEPTH_SIZE


class CameraReader:
    def __init__(self, wait_timeout: float = 5.0, copy: bool = True):
        self.copy = copy
        # tagname 으로 bridge 가 만든 공유 메모리에 붙는다. bridge 가 없으면 빈 메모리가 생기므로 magic 으로 확인.
        self._buf = mmap.mmap(-1, SHM_TOTAL, tagname=SHM_NAME, access=mmap.ACCESS_READ)
        deadline = time.monotonic() + wait_timeout
        while self._magic() != SHM_MAGIC:
            if time.monotonic() > deadline:
                self.close()
                raise TimeoutError("bridge 프레임이 없습니다. hp60c_bridge.exe 를 먼저 실행하세요.")
            time.sleep(0.05)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _magic(self) -> int:
        return struct.unpack_from("<I", self._buf, 0)[0]

    def _seq(self) -> int:
        return struct.unpack_from("<I", self._buf, 28)[0]

    def read(self, retries: int = 50):
        """가장 최근 프레임 (rgb, depth, frame_id). 없으면 None.

        bridge 가 쓰는 도중의 섞인 프레임을 거르기 위해 쓰기 순번(seq)을 복사 앞뒤로 비교한다
        (seqlock: 홀수 = 쓰는 중). copy=False 면 반환 뒤에 내용이 바뀔 수 있다.
        """
        for _ in range(retries):
            s1 = self._seq()
            if s1 & 1:  # 쓰는 중
                time.sleep(0.001)
                continue
            out = self._read_once()
            if self._seq() == s1:
                return out
        return None, None, 0

    def _read_once(self):
        if self._magic() != SHM_MAGIC:
            return None, None, 0
        rgb_w, rgb_h, _ = struct.unpack_from("<III", self._buf, 4)
        d_w, d_h, _ = struct.unpack_from("<III", self._buf, 16)
        fid = struct.unpack_from("<Q", self._buf, 32)[0]
        rgb_ready, depth_ready = struct.unpack_from("<II", self._buf, 48)
        rgb = depth = None
        if rgb_ready and rgb_w and rgb_h:
            v = np.frombuffer(self._buf, np.uint8, rgb_w * rgb_h * 3, HEADER_SIZE).reshape(
                rgb_h, rgb_w, 3
            )
            rgb = v.copy() if self.copy else v
        if depth_ready and d_w and d_h:
            v = np.frombuffer(self._buf, np.uint16, d_w * d_h, HEADER_SIZE + MAX_RGB_SIZE).reshape(
                d_h, d_w
            )
            depth = v.copy() if self.copy else v
        return rgb, depth, fid

    def read_blocking(self, last_frame_id: int = 0, timeout: float = 1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rgb, depth, fid = self.read()
            if fid > last_frame_id and (rgb is not None or depth is not None):
                return rgb, depth, fid
            time.sleep(0.005)
        return None, None, last_frame_id

    def close(self):
        if getattr(self, "_buf", None) is not None:
            self._buf.close()
            self._buf = None
