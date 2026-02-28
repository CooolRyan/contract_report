"""
pytest 공통 설정 및 픽스처.
quant-trader 루트에서 실행: pytest tests/ -v
"""
from pathlib import Path
import sys

# 프로젝트 루트(quant-trader)를 path에 추가해 core.* 임포트 가능하게
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
