"""
quant-trader 루트의 `.env` 를 `os.environ` 에 반영.

- `python-dotenv` 가 있으면 `load_dotenv(override=True)` 사용.
- 없으면 간단한 수동 파서로 동일 효과 (의존성 없이 동작).

`chart_preview` / `main` 등 어디서 실행하든 `load_quant_env()` 를 한 번 호출하면 됨.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_QUANT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _QUANT_ROOT / ".env"


def _parse_env_manual(path: Path) -> None:
    """python-dotenv 없이 KEY=VALUE 형식 로드 (UTF-8 BOM 허용)."""
    raw = path.read_text(encoding="utf-8-sig")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        val = val.replace("\\n", "\n")
        os.environ[key] = val


def load_quant_env() -> None:
    """
    `quant-trader/.env` 를 읽어 환경변수에 넣는다.
    이미 설정된 동일 키는 `.env` 값으로 덮어쓴다(override).
    """
    if not _ENV_PATH.is_file():
        log.debug("No .env at %s", _ENV_PATH)
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_PATH, override=True)
        log.debug("Loaded .env via python-dotenv: %s", _ENV_PATH)
    except ImportError:
        _parse_env_manual(_ENV_PATH)
        log.debug("Loaded .env via manual parser (install python-dotenv for full compatibility): %s", _ENV_PATH)
