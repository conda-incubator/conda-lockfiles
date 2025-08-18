import re
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# mock channel
CHANNEL_DIR = DATA_DIR / "channel"
RECIPES_DIR = DATA_DIR / "recipes"

# lockfiles
PIXI_DIR = DATA_DIR / "pixi"
PIXI_METADATA_DIR = DATA_DIR / "pixi-metadata"
CONDA_LOCK_METADATA_DIR = DATA_DIR / "conda-lock-metadata"

# Enviroments
ENVIRONMENTS_DIR = DATA_DIR / "environments"
SINGLE_PACKAGE_ENV = ENVIRONMENTS_DIR / "single_package"
SINGLE_PACKAGE_NO_URL_ENV = ENVIRONMENTS_DIR / "single_package_no_url"


RE_CREATED_BY = re.compile(r"created_by: conda-lockfiles .+")
RE_CREATED_AT = re.compile(r"created_at: .+")


def normalize_conda_lock_v1(lockfile: Path) -> str:
    text = lockfile.read_text()
    text = RE_CREATED_BY.sub("created_by: conda-lockfiles VERSION", text)
    text = RE_CREATED_AT.sub("created_at: TIMESTAMP", text)
    return text
