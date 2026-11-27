"""pytest 공통 설정: 레포 맨 위 폴더를 import 경로에 넣어 `from app.ui import ...` 가 되게 한다."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
