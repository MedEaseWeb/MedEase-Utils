import json
from pathlib import Path


def load_config(config_path: str | Path) -> dict:
    """Load a site config JSON file from config/."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Default config directory relative to this file
CONFIG_DIR = Path(__file__).parent.parent / "config"
