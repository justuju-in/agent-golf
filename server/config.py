"""Settings, read from environment variables."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Next to this file, so the default does not depend on the current directory.
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_API_BASE_URL = "http://localhost:8000"


@dataclass(frozen=True)
class Settings:
    # SQLite database (later also uploaded logs). Created at startup if missing.
    data_dir: Path = DEFAULT_DATA_DIR
    # Public origin, for absolute links in upload replies.
    api_base_url: str = DEFAULT_API_BASE_URL

    @property
    def db_path(self) -> Path:
        return self.data_dir / "agent_golf.db"


def load_settings(environ: Mapping[str, str] = os.environ) -> Settings:
    """Settings from AGENT_GOLF_DATA_DIR and AGENT_GOLF_API_BASE_URL; unset or empty means the default."""
    data_dir = environ.get("AGENT_GOLF_DATA_DIR")
    api_base_url = environ.get("AGENT_GOLF_API_BASE_URL")
    return Settings(
        data_dir=Path(data_dir) if data_dir else DEFAULT_DATA_DIR,
        api_base_url=(api_base_url or DEFAULT_API_BASE_URL).rstrip("/"),
    )
