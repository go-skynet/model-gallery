import json
import os
import shutil

from pathlib import Path
from typing import Any

def purge_folder(target: Path):
    print(f"purging folder {target}...")
    shutil.rmtree(target)
    os.makedirs(target)
    open(target / ".keep", "a").close()

def json_dump(target: Path, obj: Any):
    os.makedirs(target.parent)
    with open(target, 'w') as df:
        df.write(json.dumps(obj))
    print(f"created {target}!")