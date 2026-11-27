# ruff: noqa: E501  — 화면 안내 문장(한글)과 표 데이터가 길어서 이 화면 파일만 줄 길이 검사를 풉니다 (spikes/ 와 같은 이유)
"""모든 작업 화면 아래 "보기": 3D · 관절값 / 모터 부하 · 온도 / 카메라 6화면 (켜기·끄기 · 폴더에 촬영 · 드라이브 폴더로 복사).

전부 Mock 입니다. 실제 팔 · 카메라는 app/hw 가 생기면 그 값을 씁니다 (HP60C 는 spikes/hp60c 브리지, #37).
사진은 레포에 올리지 않도록 logs/hanbang/photos/ (Git 제외)에 저장합니다.
"""

from __future__ import annotations

import io
import json
import re
import shutil
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw

from app.ui import widgets as w

ASSET = Path(__file__).resolve().parent / "assets" / "so101_lowpoly.json"
CAMS = [
    ("left", "1", "왼쪽 암", False),
    ("right", "2", "오른쪽 암", False),
    ("side", "3", "측면", False),
    ("sideD", "3-깊이", "측면 깊이", True),
    ("top", "4", "위", False),
    ("topD", "4-깊이", "위 깊이", True),
]
LIM = {"load_w": 60, "load_d": 85, "temp_w": 55, "temp_d": 65}  # 모터 주의 · 위험 기준
FOLDER_RE = re.compile(r"^[0-9A-Za-z가-힣_\-]{1,40}$")
MOTORS = ["받침", "어깨", "팔꿈치", "손목 꺾기", "손목 돌리기", "그리퍼"]

# so101.urdf 의 관절 · 링크 (3D 보기용)
URDF = {
    "links": {
        "base_link": [
            [
                "base_motor_holder_so101_v1",
                [-0.00636471, -9.94414e-05, -0.0024],
                [1.5708, 0, 1.5708],
                "p",
            ],
            ["base_so101_v2", [-0.00636471, 0, -0.0024], [1.5708, 0, 1.5708], "p"],
            ["sts3215_03a_v1", [0.0263353, 0, 0.0437], [0, 0, 0], "m"],
            [
                "waveshare_mounting_plate_so101_v2",
                [-0.0309827, -0.000199441, 0.0474],
                [1.5708, 0, 1.5708],
                "p",
            ],
        ],
        "shoulder_link": [
            ["sts3215_03a_v1", [-0.0303992, 0.000422241, -0.0417], [1.5708, 1.5708, 0], "m"],
            [
                "motor_holder_so101_base_v1",
                [-0.0675992, -0.000177759, 0.0158499],
                [1.5708, -1.5708, 0],
                "p",
            ],
            ["rotation_pitch_so101_v1", [0.0122008, 2.22413e-05, 0.0464], [-1.5708, 0, 0], "p"],
        ],
        "upper_arm_link": [
            ["sts3215_03a_v1", [-0.11257, -0.0155, 0.0187], [-3.14159, 0, -1.5708], "m"],
            ["upper_arm_so101_v1", [-0.065085, 0.012, 0.0182], [3.14159, 0, 0], "p"],
        ],
        "lower_arm_link": [
            ["under_arm_so101_v1", [-0.0648499, -0.032, 0.0182], [3.14159, 0, 0], "p"],
            ["motor_holder_so101_wrist_v1", [-0.0648499, -0.032, 0.018], [-3.14159, 0, 0], "p"],
            ["sts3215_03a_v1", [-0.1224, 0.0052, 0.0187], [-3.14159, 0, -3.14159], "m"],
        ],
        "wrist_link": [
            ["sts3215_03a_no_horn_v1", [0, -0.0424, 0.0306], [1.5708, 1.5708, 0], "m"],
            ["wrist_roll_pitch_so101_v2", [0, -0.028, 0.0181], [-1.5708, -1.5708, 0], "p"],
        ],
        "gripper_link": [
            ["sts3215_03a_v1", [0.0077, 0.0001, -0.0234], [-1.5708, 0, 0], "m"],
            ["wrist_roll_follower_so101_v1", [0, -0.000218214, 0.000949706], [-3.14159, 0, 0], "p"],
        ],
        "moving_jaw_so101_v1_link": [["moving_jaw_so101_v1", [0, 0, 0.0189], [0, 0, 0], "p"]],
    },
    "joints": [
        [
            "shoulder_pan",
            "base_link",
            "shoulder_link",
            [0.0388353, 0, 0.0624],
            [3.14159, 0, -3.14159],
        ],
        [
            "shoulder_lift",
            "shoulder_link",
            "upper_arm_link",
            [-0.0303992, -0.0182778, -0.0542],
            [-1.5708, -1.5708, 0],
        ],
        ["elbow_flex", "upper_arm_link", "lower_arm_link", [-0.11257, -0.028, 0], [0, 0, 1.5708]],
        ["wrist_flex", "lower_arm_link", "wrist_link", [-0.1349, 0.0052, 0], [0, 0, -1.5708]],
        [
            "wrist_roll",
            "wrist_link",
            "gripper_link",
            [0, -0.0611, 0.0181],
            [1.5708, 0.0486795, 3.14159],
        ],
        [
            "gripper",
            "gripper_link",
            "moving_jaw_so101_v1_link",
            [0.0202, 0.0188, -0.0234],
            [1.5708, 0, 0],
        ],
    ],
}

THREE_HTML = """
<div id="v" style="width:100%;height:360px;border-radius:10px;background:#e7eaee;position:relative"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
const MESH=__MESH__, U=__URDF__, JF=__JF__, JL=__JL__, DUAL=__DUAL__;
const host=document.getElementById("v");
function geo(m){const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(new Float32Array(m.v.map(x=>x/1000)),3));g.setIndex(m.f);g.computeVertexNormals();return g}
const G={};for(const k in MESH)G[k]=geo(MESH[k]);
function q(k,v){return k===5?-0.174533+(v/100)*(1.74533+0.174533):v*Math.PI/180}
function arm(cp,j){const mp=new THREE.MeshStandardMaterial({color:cp,roughness:.6,flatShading:true,side:THREE.DoubleSide}),mm=new THREE.MeshStandardMaterial({color:0x2a2a2a,flatShading:true,side:THREE.DoubleSide});
 const gr={};for(const ln in U.links){const g=new THREE.Group();gr[ln]=g;for(const [n,xyz,rpy,t] of U.links[ln]){const o=new THREE.Mesh(G[n+".stl"],t==="p"?mp:mm);o.position.set(...xyz);o.rotation.set(rpy[0],rpy[1],rpy[2],"ZYX");g.add(o)}}
 U.joints.forEach(([n,p,c,xyz,rpy],k)=>{const jo=new THREE.Group();jo.position.set(...xyz);jo.rotation.set(rpy[0],rpy[1],rpy[2],"ZYX");const r=new THREE.Group();r.rotation.z=q(k,j[k]);jo.add(r);r.add(gr[c]);gr[p].add(jo)});
 const h=new THREE.Group();h.rotation.x=-Math.PI/2;h.add(gr.base_link);return h}
const sc=new THREE.Scene();sc.add(new THREE.HemisphereLight(0xffffff,0x667080,.9));const dl=new THREE.DirectionalLight(0xffffff,.8);dl.position.set(.5,1,.6);sc.add(dl);
sc.add(new THREE.GridHelper(0.8,16,0x8a949c,0xb8c0c6));
const mir=j=>[-j[0],j[1],j[2],j[3],-j[4],j[5]];
const add=(o,x,z)=>{o.position.set(x,0,z);sc.add(o)};
if(DUAL){add(arm(0xf2c12e,JF),0,0.17);add(arm(0xf2c12e,mir(JF)),0,-0.17);add(arm(0x6f9be8,JL),-0.5,0.17);add(arm(0x6f9be8,mir(JL)),-0.5,-0.17)}
else{add(arm(0xf2c12e,JF),0,0);add(arm(0x6f9be8,JL),0,-0.32)}
const cam=new THREE.PerspectiveCamera(40,host.clientWidth/360,.01,10);cam.position.set(.62,.5,.62);
const rd=new THREE.WebGLRenderer({antialias:true,alpha:true});rd.setSize(host.clientWidth,360);host.appendChild(rd.domElement);
const ctl=new THREE.OrbitControls(cam,rd.domElement);ctl.target.set(-0.1,0.1,-0.1);ctl.update();
(function loop(){rd.render(sc,cam);requestAnimationFrame(loop)})();
</script>
<div style="font:12px sans-serif;color:#55606a;margin-top:4px">노랑 = 팔로워 · 파랑 = 리더 · 마우스로 돌리기/확대</div>
"""


@st.cache_data
def _mesh() -> str:
    return ASSET.read_text(encoding="utf-8")


def _arm_3d(jf: list[int], jl: list[int], dual: bool) -> None:
    if not ASSET.exists():
        st.info("3D 메시 파일(app/ui/assets/so101_lowpoly.json)이 없어 관절값 표만 보여 줍니다.")
        return
    html = (
        THREE_HTML.replace("__MESH__", _mesh())
        .replace("__URDF__", json.dumps(URDF))
        .replace("__JF__", json.dumps(jf))
        .replace("__JL__", json.dumps(jl))
        .replace("__DUAL__", "true" if dual else "false")
    )
    components.html(html, height=390)


def _frame(cam_id: str, depth: bool, on: bool) -> Image.Image:
    """예시 카메라 화면 (Mock)."""
    img = Image.new(
        "RGB", (320, 240), (26, 29, 32) if not on else ((30, 60, 110) if depth else (91, 95, 99))
    )
    g = ImageDraw.Draw(img)
    if not on:
        g.text((140, 112), "OFF", fill=(138, 148, 156))
        return img
    cols = [
        (42, 99, 201),
        (226, 179, 60),
        (210, 58, 50),
        (31, 138, 91),
        (224, 123, 46),
        (232, 232, 232),
    ]
    if cam_id in ("left", "right"):
        g.rectangle((130, 70, 190, 130), fill=cols[0] if cam_id == "left" else cols[2])
    else:
        for i, c in enumerate(cols):
            x, y = 30 + (i % 3) * 44, 30 + (i // 3) * 44
            g.rectangle((x, y, x + 24, y + 24), fill=(200, 200, 200) if depth else c)
    g.rectangle((0, 0, 320, 16), fill=(0, 0, 0))
    g.text((6, 3), f"{cam_id} · {'DEPTH' if depth else 'COLOR'} · MOCK", fill=(255, 255, 255))
    return img


def _png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def views() -> None:
    ss = st.session_state
    jf, jl = w.joints(), ss.get("jl", list(w.REST))
    st.divider()
    st.markdown("#### 보기")
    c1, c2, c3 = st.columns(3)
    show3d = c1.toggle("3D · 관절값", value=ss.get("v3d", False), key="v3d")
    showm = c2.toggle("모터 부하 · 온도", value=ss.get("vm", False), key="vm")
    showc = c3.toggle("카메라 4대", value=ss.get("vc", False), key="vc")
    if show3d:
        with st.container(border=True):
            dual = st.toggle(
                "양팔 보기 (손수건)", value=ss.task == "fold_cloth", key=f"dual_{ss.task}"
            )
            left, right = st.columns([3, 2])
            with left:
                _arm_3d(ss.get("preview") or jf, jl, dual)
            with right:
                w.table(
                    [
                        {
                            "관절": w.JL[k],
                            "리더": jl[k],
                            "팔로워": jf[k],
                            "차이": jl[k] - jf[k],
                            "범위": f"{w.JMIN[k]}~{w.JMAX[k]}",
                        }
                        for k in range(6)
                    ]
                )
                if ss.get("preview"):
                    st.caption("3D 는 미리보기 자세입니다 (실제 팔은 안 움직임)")
                    if st.button("미리보기 끄기"):
                        ss.preview = None
                        st.rerun()
                if st.button("원격조작 한 번 움직이기 (Mock)"):
                    import random

                    ss.jl = w.clamp_joints(
                        [
                            random.uniform(lo * 0.4, hi * 0.4)
                            for lo, hi in zip(w.JMIN, w.JMAX, strict=True)
                        ]
                    )
                    ss.jf = list(ss.jl)
                    st.rerun()
    if showm:
        with st.container(border=True):
            st.caption(
                f"팔로워 STS3215 × 6 · 예시 값 · 부하 {LIM['load_w']}% 주의 · {LIM['load_d']}% 위험 / 온도 {LIM['temp_w']}°C 주의 · {LIM['temp_d']}°C 위험 → 위험이면 자동 정지"
            )
            rows, bad = [], []
            for k, name in enumerate(MOTORS):
                load = min(100, abs(jl[k] - jf[k]) * 2 + (25 if k in (1, 2) else 8))
                temp = 31 + load / 8
                st_ = (
                    "위험"
                    if load >= LIM["load_d"] or temp >= LIM["temp_d"]
                    else "주의"
                    if load >= LIM["load_w"] or temp >= LIM["temp_w"]
                    else "정상"
                )
                rows.append(
                    {
                        "ID": k + 1,
                        "모터": name,
                        "부하 %": round(load),
                        "온도 °C": round(temp, 1),
                        "상태": st_,
                    }
                )
                if st_ != "정상":
                    bad.append(f"{k + 1} {name} {st_}")
            st.dataframe(
                rows,
                hide_index=True,
                width="stretch",
                column_config={
                    "부하 %": st.column_config.ProgressColumn("부하 %", min_value=0, max_value=100)
                },
            )
            if bad:
                st.warning("모터 " + " · ".join(bad) + " — 쉬게 하거나 속도를 낮추세요")
    if showc:
        _cams()


def _cams() -> None:
    ss = st.session_state
    ss.setdefault("cam_on", {c[0]: True for c in CAMS})
    with st.container(border=True):
        st.caption(
            "1 왼쪽 암 · 2 오른쪽 암 · 3 측면 · 4 위 (3 · 4 는 깊이 화면을 따로) · 연결 전이라 예시 화면"
        )
        c1, c2, c3 = st.columns([2, 1, 1])
        folder = c1.text_input(
            "저장 폴더 이름", placeholder="블록_1차_오전", key=f"folder_{ss.task}"
        )
        ok_folder = bool(FOLDER_RE.match(folder.strip()))
        if folder and not ok_folder:
            st.error("폴더 이름은 한글·영어·숫자·_·- 로 1~40자 (띄어쓰기 대신 _ )")
        base = w.HANBANG_DIR / "photos" / ss.task / folder.strip() if ok_folder else None
        snap_all = c2.button("● 켜진 카메라 모두 촬영", disabled=not ok_folder)
        cols = st.columns(3)
        shots = []
        for i, (cid, no, name, depth) in enumerate(CAMS):
            with cols[i % 3]:
                on = st.toggle(f"{no}. {name}", value=ss.cam_on[cid], key=f"camon_{cid}")
                ss.cam_on[cid] = on
                img = _frame(cid, depth, on)
                st.image(img, width="stretch")
                if st.button("● 촬영", key=f"snap_{cid}", disabled=not (on and ok_folder)) or (
                    snap_all and on
                ):
                    shots.append((cid, img))
        if shots and base:
            base.mkdir(parents=True, exist_ok=True)
            for cid, img in shots:
                n = len(list(base.glob(f"{cid}_*.png"))) + 1
                (base / f"{cid}_{n:03d}.png").write_bytes(_png(img))
            st.toast(f"{len(shots)}장 저장 → {base.relative_to(w.ROOT)}")
        if base and base.exists():
            files = sorted(base.glob("*.png"))
            st.markdown(f"**{base.relative_to(w.ROOT)}** · {len(files)}장 (레포에 올리지 않음)")
            if files:
                st.image(
                    [str(f) for f in files[-12:]], caption=[f.name for f in files[-12:]], width=110
                )
            drive = c3.text_input(
                "구글 드라이브 폴더 (Drive 앱 경로)",
                placeholder=r"G:\내 드라이브\Thursday",
                key="drive_dir",
            )
            if st.button("구글 드라이브 폴더로 복사", disabled=not files):
                dst = (
                    Path(drive.strip()) / "data" / ss.task / folder.strip()
                    if drive.strip()
                    else None
                )
                if not dst or not Path(drive.strip()).exists():
                    st.error(
                        "드라이브 폴더가 없습니다. Google Drive 데스크톱 앱을 켜고 그 폴더 경로를 넣어 주세요 (로그인은 각자 직접)."
                    )
                else:
                    dst.mkdir(parents=True, exist_ok=True)
                    for f in files:
                        shutil.copy2(f, dst / f.name)
                    st.success(f"{len(files)}장 복사 → {dst}")
