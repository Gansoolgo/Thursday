# 실험 기록: Windows 11에서 LeRobot으로 SO-101 두 쌍(리더암 1 → 팔로워암 1, 리더암 2 → 팔로워암 2) 보정·원격조작

- **날짜:** 2026-11-27
- **작성자:** 신재석 (AI 초안: Claude Code)
- **관련 Issue:** #3 (담당 구경윤, 이 기록은 미리 해 본 결과), #2
- **결과 한 줄:** 🔶 부분 성공 — 두 쌍 모두 Windows에서 보정·원격조작까지 됨(한 쌍씩). 양팔 동시 동작은 아직. IK용 `lerobot[kinematics]`는 Windows 설치 실패

## 1. 목적
#3 GO 기준(Windows에서 연결·보정·원격조작 1분)을 11/28 전에 한 쌍으로 미리 확인하고, 막힐 곳을 찾는다.

## 2. 환경
| 항목 | 값 |
|---|---|
| 장치 | LENOVO 21SK, Intel Core Ultra 5 225H, RAM 16GB |
| OS | Windows 11 Pro (빌드 26300) |
| 주요 버전 | Python 3.12.10 (`.venv`), lerobot 0.7.0, torch 2.15.0, numpy 2.2.6, openvino 2026.4.1 |
| 하드웨어 상태 | 팔로워암 1 = 12V 2A 어댑터, 리더암 1 = 5V 3A 어댑터. 두 팔 USB를 노트북에 꽂음 (유전원 허브 안 씀). 손목 카메라 연결됨 |
| 포트 | 팔로워암 1 = COM6 (CH343, 시리얼 5B3D041258) / 리더암 1 = COM7 (5AAF218987) / 팔로워암 2 = COM9 (5B3D044237) / 리더암 2 = COM8 (5B90149145). 2쌍째는 1쌍을 뽑고 꽂음. 리더·팔로워 구분은 모터 전압으로 (팔로워 12.2~12.4V, 리더 5.2~5.3V) |

## 3. 방법
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install "lerobot[feetech]"
.venv\Scripts\lerobot-find-cameras.exe opencv
.venv\Scripts\lerobot-calibrate.exe --robot.type=so101_follower --robot.port=COM6 --robot.id=follower_1
.venv\Scripts\lerobot-calibrate.exe --teleop.type=so101_leader --teleop.port=COM7 --teleop.id=leader_1
.venv\Scripts\lerobot-teleoperate.exe --robot.type=so101_follower --robot.port=COM6 --robot.id=follower_1 --teleop.type=so101_leader --teleop.port=COM7 --teleop.id=leader_1
# 2쌍째
.venv\Scripts\lerobot-calibrate.exe --robot.type=so101_follower --robot.port=COM9 --robot.id=follower_2
.venv\Scripts\lerobot-calibrate.exe --teleop.type=so101_leader --teleop.port=COM8 --teleop.id=leader_2
.venv\Scripts\lerobot-teleoperate.exe --robot.type=so101_follower --robot.port=COM9 --robot.id=follower_2 --teleop.type=so101_leader --teleop.port=COM8 --teleop.id=leader_2
```
- 보정 첫 자세: 화면 그림대로 **ㄱ자**(윗팔 수직, 아랫팔 수평, 손목 일직선, 손잡이 아래)
- `.venv\Scripts\activate` 없이 실행 파일 경로를 직접 붙여 씀 (activate 안 하면 `lerobot-calibrate` 명령을 못 찾음)

## 4. 결과
| 항목 | 결과 | 메모 |
|---|---|---|
| lerobot 설치 (`[feetech]`) | ✅ | 0.7.0 |
| `lerobot[kinematics]` 설치 | ❌ | 아래 5장 |
| 양팔 설정 `bi_so_follower`·`bi_so_leader` | ✅ import 성공 | 0.7.0에 포함. 실제 양팔 동작은 아직 안 해 봄 |
| 모터 응답 (ID 1~6) | ✅ 두 팔 모두 6개, 모델 777 (STS3215) | 모터 ID 설정(`setup-motors`) 필요 없음 |
| 손목 카메라 | ✅ opencv 1번, 640×480 YUY2 | 0번은 노트북 내장 카메라 |
| 팔로워암 1 보정 | ✅ (2번째 시도) | 아래 표 |
| 리더암 1 보정 | ✅ (2번째 시도) | 아래 표 |
| 원격조작 1쌍 (리더암 1 → 팔로워암 1) | ✅ "잘 됨" (신재석 확인) | 지속 시간 1분 이상인지·끊김 횟수: (확인 필요) |
| 팔로워암 2 · 리더암 2 보정 | ✅ (첫 시도) | 아래 표 |
| 원격조작 2쌍 (리더암 2 → 팔로워암 2) | ✅ "다 했음" (신재석 확인) | 1분 이상·영상 10초: (확인 필요) |

보정 범위 (MIN ~ MAX, 0~4095 = 한 바퀴)

| 관절 | 팔로워암 1 | 리더암 1 | 팔로워암 2 | 리더암 2 |
|---|---|---|---|---|
| shoulder_pan | 608 ~ 3359 | 753 ~ 3462 | 737 ~ 3283 | 706 ~ 3435 |
| shoulder_lift | 843 ~ 3249 | 839 ~ 3276 | 875 ~ 3277 | 899 ~ 3280 |
| elbow_flex | 831 ~ 3051 | 824 ~ 3035 | 827 ~ 3063 | 796 ~ 3006 |
| wrist_flex | 817 ~ 3135 | 864 ~ 3237 | 806 ~ 3193 | 887 ~ 3231 |
| gripper | 2017 ~ 3558 | 1869 ~ 3225 | 1985 ~ 3567 | 2018 ~ 3369 |

- 사진·영상: (확인 필요) — #3 확인 방법은 원격조작 영상 10초

## 5. 잘 안 된 것과 원인
1. **kinematics 설치 실패:** `pip install "lerobot[kinematics]"` → `Failed to build 'placo'` (`Failed to build 'eiquadprog'`). placo 0.9.x는 Windows용 휠이 없음. Windows용 휠이 있는 대안: `ikpy` (확인함). → 당장은 티칭 방식(dependencies.md R2)으로 진행 제안
2. **팔로워 첫 보정 값 이상:** shoulder_lift 0~4092, elbow_flex 0~4095 (경계를 넘은 값). 첫 자세가 가운데에서 벗어났거나 통신 오류로 추정. ㄱ자 자세로 다시 하니 정상
3. **일시적 통신 오류:** `ConnectionError: Failed to enable torque after 1 tries on 'wrist_flex' (motor ID 4): Checksum error.` → 다시 실행하니 됨
4. **리더 모터 전부 응답 없음:** `RuntimeError: SerialMotorsBus motor check failed on port 'COM7': Missing motor IDs: 1~6` → 잠시 뒤 다시 확인하니 6개 모두 응답. 리더 전원 연결 문제로 추정 (확인 필요)
5. **리더 집게 범위 누락:** 첫 보정에서 gripper 2047~2053 → 집게를 끝까지 열고 닫아 다시 함
6. 재보정 때 "Press ENTER to use provided calibration file ... or type 'c'"에서 Enter만 누르면 **예전 파일을 그대로 씀** → `c` 입력 필요

## 6. 결론과 다음 할 일
- **결론:** Windows 11에서 LeRobot 0.7.0으로 SO-101 **두 쌍 모두** 보정과 원격조작이 된다(한 쌍씩). #3의 대안(WSL·feetech 직접 제어)은 지금은 필요 없어 보인다. 단, IK(placo)는 Windows에서 바로 안 된다.
- **다음:**
  - 원격조작 1분 연속·영상 10초 (#3 확인 방법)
  - 4대를 동시에 꽂고 양팔 `bi_so_follower`·`bi_so_leader` (#40) — 노트북 포트가 4개뿐이라 유전원 허브 필요
  - IK 방법 결정 (티칭 먼저, 손 위 전달 때 ikpy 시험) — 구경윤과 #4 전에
  - 유전원 허브로 옮기면 COM 번호 다시 확인
- results-m1.md / decisions.md 반영: 안 함 (#3은 구경윤 확인 후)
