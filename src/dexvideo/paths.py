from pathlib import Path
import os
REPO = Path(__file__).resolve().parents[2]
def stage(name):
    root = Path(os.environ.get('DEXVIDEO_WORK', REPO / 'work')).expanduser().resolve()
    p = root / name
    p.mkdir(parents=True, exist_ok=True)
    return p
