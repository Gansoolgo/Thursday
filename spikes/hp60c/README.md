# HP60C 깊이 카메라 — Windows에서 컬러 + 깊이 받기 (spike, #37)

> **📌 3줄 요약**
> - HP60C를 Windows 노트북에서 Python으로 **컬러 640×480 + 깊이 640×480(mm)** 받는 코드입니다. 11/27 시험: 약 10 fps.
> - 제조사 SDK는 독점 라이선스라 **저장소에 없습니다.** 아래 1~2단계로 각자 받아서 빌드합니다 (처음 한 번 약 30분).
> - 깊이가 필요 없고 **컬러만** 보려면 SDK 없이 `camera_view.py`만 쓰면 됩니다.
>
> 시험 기록: [2026-11-27_37_hp60c-windows.md](../../docs/records/experiments/2026-11-27_37_hp60c-windows.md) · 결정: [D-15](../../docs/plan/decisions.md)

## 구조

```
HP60C ─USB─▶ AngstrongCameraSdk.dll ─▶ hp60c_bridge.exe ─▶ 공유 메모리 "Local\hp60c_frames" ─▶ Python (hp60c_reader.py)
```

일반 웹캠 방식(OpenCV `VideoCapture`)으로는 **컬러만** 나오고 깊이는 안 나옵니다. 깊이는 제조사 SDK를 거쳐야 해서, C++ 프로그램(bridge)이 SDK에서 받아 공유 메모리에 쓰고 Python은 그걸 읽습니다.
bridge 코드는 외부 저장소 `th2102da/hp60c-camera`(MIT, Linux용)를 Windows로 옮긴 것입니다.

| 파일 | 하는 일 |
|---|---|
| `bridge_win.cpp` | SDK → 공유 메모리 (C++) |
| `make_def.py` | SDK DLL에서 연결용 `.lib` 재료 만들기 (제조사가 `.lib`를 안 줌) |
| `build.ps1` | 빌드 한 번에 |
| `hp60c_reader.py` | Python에서 `rgb, depth = cam.read()` |
| `view_rgbd.py` | 컬러·깊이 나란히 보기, 마우스 위치 거리(mm) |
| `camera_view.py` | **SDK 없이** 컬러만 보기 + 판 모서리 클릭으로 설치 위치 맞추기 |

## 처음 한 번: 준비

### 1단계. SDK 헤더 (4개 파일)
- `th2102da/hp60c-camera` 저장소의 `sdk/libs/include/` 안 `.h` 파일 4개를 **`spikes/hp60c/sdk_include/`** 에 넣습니다.
- 그 저장소는 private입니다. 접근이 필요하면 팀 채널에 GitHub 계정을 알려 초대를 받으세요.
- `sdk_include/`는 `.gitignore`로 제외되어 있어 실수로 커밋되지 않습니다.

### 2단계. Windows SDK (뷰어에 들어 있음)
1. 판매처(Yahboom) 공유 드라이브 `E41_NUWA_HP60C_DepthCamera` → `0.VM_File/7.SoftWare/Windows Software.zip` (129MB)을 받습니다.
   (드라이브 링크: [Yahboom HP60C GitHub](https://github.com/YahboomTechnology/Nuwa-HP60C-Depth-Camera)의 `Annex_Download_Link.txt`)
2. **영어로만 된 경로**에 풉니다: `C:\hp60c`. 안의 `.7z`도 같은 곳에 풉니다 (반디집·7-Zip, 또는 `tar -xf 파일.7z`).
   → `C:\hp60c\RelWithDebInfo\AngstrongCameraSdk.dll` 이 생기면 됩니다.
   SDK가 한글·중국어 경로를 싫어합니다.
3. (선택) `AngstrongViewer.exe`로 깊이가 나오는지 먼저 확인. 서명 없는 프로그램이라 백신 검사 권장.

### 3단계. C++ 빌드 도구
```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --source winget --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.26100"
```
약 2~6GB, 10~20분. 관리자 권한 창이 뜨면 "예".

### 4단계. 빌드
```powershell
cd spikes\hp60c
.\build.ps1
```
결과: `C:\hp60c\bridge\hp60c_bridge.exe` (+ 필요한 DLL·설정 파일 복사)

## 쓸 때마다

1. **터미널 A** — bridge 켜 두기
   ```powershell
   C:\hp60c\bridge\hp60c_bridge.exe C:\hp60c\bridge\configurationfiles
   ```
2. `No device found` 가 나오고 `Streaming started` 가 안 나오면 → **HP60C를 뽑았다가 다시 꽂기.**
   Windows SDK가 이미 꽂혀 있던 카메라를 **가끔** 못 찾습니다. 다시 꽂으면 그 순간 감지합니다 (11/27: 첫 실행은 다시 꽂아야 했고, 두 번째 실행은 바로 잡힘).
3. **터미널 B** — 보기
   ```powershell
   cd spikes\hp60c
   python view_rgbd.py          # 카메라를 거꾸로 달았으면 --flip
   ```
   파랑 = 가까움, 빨강 = 멂, 검정 = 깊이 없음. `s` 저장, `q`/ESC/X 종료.

코드에서:
```python
from hp60c_reader import CameraReader

with CameraReader() as cam:
    rgb, depth, fid = cam.read_blocking()
    # rgb: BGR uint8 (480, 640, 3) / depth: uint16 mm (480, 640), 0 = 깊이 없음
```

## 컬러만 볼 때 (SDK 필요 없음)
```powershell
python camera_view.py --list                    # HP60C 번호 찾기 (장치 이름 "ASJ ZNX_NVT")
python camera_view.py --cam 1 --board 900x600   # 판 크기 mm
```
- **DSHOW 방식으로 열면 검은 화면**이고 MSMF로 열어야 나옵니다 (코드에 반영됨).
- 해상도를 지정하면 안 나옵니다. 기본값(640×642)으로 둡니다.

## 카메라 설치 위치 계산
`spikes/camera_placement/`
- `camera_height.py` — 정면(상부) 카메라 높이별 시야·사각지대. 결과: A2 판 약 50cm, A1 판 약 65~70cm
- `side_camera.py` — 측면 카메라 위치. 결과: 정면 60~70cm일 때 측면 높이 40~50cm, 판에서 30~40cm 밖, 약 25~30° 내려다보기

시야각만 판매처 값이고 나머지(손 높이 25cm, 팔 높이 40cm 등)는 가정입니다.

## 공유 메모리 레이아웃
`th2102da/hp60c-camera`(Linux)와 같고, 헤더의 `_pad` 자리(오프셋 28)를 **쓰기 순번 `seq`** 로 씁니다.
bridge는 쓰기 전에 홀수, 다 쓴 뒤 짝수로 올리고, reader는 복사 앞뒤 `seq`가 같고 짝수일 때만 받아들입니다 (쓰는 도중 섞인 프레임 방지).

## 주의
- **카메라는 한 프로그램만** 쓸 수 있습니다. bridge·뷰어·`camera_view.py`를 동시에 못 씀.
- 프로그램이 멈춰 카메라를 계속 잡고 있으면: 작업 관리자에서 python을 끄고 카메라를 다시 꽂기.
- 아직 안 된 것: 다시 꽂지 않고 연결, **두 대 동시**(bridge는 지금 1대만), 두 대의 적외선 간섭 시험.
- SDK 헤더는 Linux판(2023-03), DLL은 Windows판(v1.2.13)입니다. 지금 쓰는 함수는 문제없었지만 다른 기능을 쓸 때는 구조 차이를 확인하세요.
