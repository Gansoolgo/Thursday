"""AngstrongCameraSdk.dll 의 내보낸 함수 목록으로 .def 파일을 만든다.

제조사가 .lib(가져오기 라이브러리)를 주지 않아서, MSVC `lib /def:` 로 .lib 를 만들 때 쓴다.
사용법: python make_def.py C:\\hp60c\\RelWithDebInfo\\AngstrongCameraSdk.dll build\\AngstrongCameraSdk.def
"""

import struct
import sys
from pathlib import Path


def exports(dll_path):
    d = Path(dll_path).read_bytes()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", d, opt)[0]
    if magic != 0x20B:
        raise SystemExit("x64 DLL이 아닙니다")
    exp_rva = struct.unpack_from("<I", d, opt + 112)[0]
    sh = opt + struct.unpack_from("<H", d, pe + 20)[0]
    secs = [struct.unpack_from("<8sIIII", d, sh + 40 * i) for i in range(nsec)]

    def off(rva):
        for _, vs, va, rs, rp in secs:
            if va <= rva < va + max(vs, rs):
                return rva - va + rp
        raise ValueError(rva)

    base = off(exp_rva)
    n_names = struct.unpack_from("<I", d, base + 24)[0]
    names_rva = struct.unpack_from("<I", d, base + 32)[0]
    out = []
    for i in range(n_names):
        o = off(struct.unpack_from("<I", d, off(names_rva) + 4 * i)[0])
        out.append(d[o : d.index(b"\0", o)].decode("ascii"))
    return out


def main():
    dll, out = sys.argv[1], sys.argv[2]
    names = exports(dll)
    need = [
        "AS_SDK_Init",
        "AS_SDK_Deinit",
        "AS_SDK_CreateCamHandle",
        "AS_SDK_DestoryCamHandle",
        "AS_SDK_OpenCamera",
        "AS_SDK_CloseCamera",
        "AS_SDK_GetCameraModel",
        "AS_SDK_GetCamParameter",
        "AS_SDK_RegisterStreamCallback",
        "AS_SDK_StartStream",
        "AS_SDK_StopStream",
        "AS_SDK_StartListener",
        "AS_SDK_StopListener",
    ]
    for n in need:
        hits = [x for x in names if x.startswith(f"?{n}@@")]
        print(f"{n:32} {'OK ' + hits[0] if hits else '없음!'}")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(
        "LIBRARY AngstrongCameraSdk\nEXPORTS\n" + "\n".join(f"  {n}" for n in names) + "\n",
        encoding="ascii",
    )
    print(f"{len(names)}개 이름 -> {out}")


if __name__ == "__main__":
    main()
