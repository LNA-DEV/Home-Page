"""Import a script whose filename has dashes.

`scripts/gallery-embed-metadata.py`, `scripts/sync-gallery.py` and the sync
scripts are commands, not modules, so their names are not importable. They are
still where the pure functions live, and those are what these tests are for.
"""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"

# The dashless modules (gallery_common, gallery_xmp, dex_common) import normally
# once scripts/ is on the path — and the dashed ones import them by name.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name):
    """Import scripts/<name>.py under a dashless module name."""
    path = SCRIPTS / f"{name}.py"
    module_name = "script_" + name.replace("-", "_")
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
