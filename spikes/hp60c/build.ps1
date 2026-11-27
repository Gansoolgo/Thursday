# HP60C Windows bridge 빌드 (MSVC Build Tools 필요)
#
# 하는 일
#   1) AngstrongCameraSdk.dll 내보내기 목록 -> .def -> .lib (제조사가 .lib 를 주지 않아서)
#   2) bridge_win.cpp 컴파일 (/MD: DLL 과 같은 릴리스 런타임)
#   3) 실행에 필요한 DLL·설정 파일을 build\ 로 복사
#
# 사용법 (PowerShell):  .\build.ps1
# SDK 위치를 바꾸려면:  .\build.ps1 -SdkDir C:\hp60c\RelWithDebInfo -IncludeDir C:\path\to\include

param(
    [string]$SdkDir = "C:\hp60c\RelWithDebInfo",
    # SDK 헤더 4개(as_camera_sdk_api.h 등)를 넣어 둘 폴더. 독점 라이선스라 Git에서 제외됨 (README 1단계)
    [string]$IncludeDir = "$PSScriptRoot\sdk_include",
    # SDK 설명서: 한글·중국어가 없는 경로에서 실행할 것 -> 결과물은 영어 경로에 둔다
    [string]$OutDir = "C:\hp60c\bridge"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path "$IncludeDir\as_camera_sdk_api.h")) { throw "SDK 헤더가 없습니다: $IncludeDir (README 1단계)" }
$build = $OutDir
New-Item -ItemType Directory -Force $build | Out-Null

# MSVC 환경 찾기
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "Visual Studio Build Tools 가 없습니다." }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw "C++ 빌드 도구(VC.Tools.x86.x64)가 설치되지 않았습니다." }
$vcvars = Join-Path $vs "VC\Auxiliary\Build\vcvars64.bat"
# vcvars64.bat 이 vswhere 를 PATH 에서 찾다가 실패 코드를 내지 않도록 Installer 폴더를 PATH 에 추가
$env:PATH = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer;$env:PATH"

# 1) .def -> .lib
python -I "$PSScriptRoot\make_def.py" "$SdkDir\AngstrongCameraSdk.dll" "$build\AngstrongCameraSdk.def"
if ($LASTEXITCODE -ne 0) { throw "make_def 실패" }

# 2) 컴파일 (vcvars 환경에서 한 번에)
# cmd /c 는 여러 줄 문자열의 첫 줄만 실행하므로 한 줄로 이어 붙인다
$cmd = "call `"$vcvars`" >nul && cd /d `"$build`" && " +
       "lib /nologo /def:AngstrongCameraSdk.def /machine:x64 /out:AngstrongCameraSdk.lib && " +
       "cl /nologo /EHsc /std:c++17 /O2 /MD /utf-8 /I`"$IncludeDir`" `"$PSScriptRoot\bridge_win.cpp`" /Fe:hp60c_bridge.exe /link AngstrongCameraSdk.lib"
cmd /c $cmd
if ($LASTEXITCODE -ne 0) { throw "컴파일 실패" }

# 3) 실행에 필요한 파일 복사 (SDK DLL 과 그 의존 DLL, 설정 파일)
foreach ($f in "AngstrongCameraSdk.dll", "AngKondyorArith.dll", "libzmq.dll", "SonixCamera.dll",
               "CH375DLL64.dll", "WCH55xISPDLL.dll", "opencv_world341.dll", "opencv_world3412.dll") {
    if (Test-Path "$SdkDir\$f") { Copy-Item "$SdkDir\$f" $build -Force }
}
Copy-Item "$SdkDir\configurationfiles" "$build\configurationfiles" -Recurse -Force
Write-Host "빌드 완료: $build\hp60c_bridge.exe"
