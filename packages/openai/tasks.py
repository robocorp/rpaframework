import sys
from pathlib import Path

from invoke import Collection

REPO_ROOT = Path(__file__).parents[2].resolve()
PACKAGE_DIR = REPO_ROOT / "packages" / "openai"

# Note to VSCode users, in order to eliminate Pylance import errors
# in the IDE, you must add the following settings to your local project
# .vscode/settings.json file:
#
#     "python.analysis.extraPaths": [
#        "./invocations"
#    ]
sys.path.append(str(REPO_ROOT))
import invocations


configuration = {
    "is_meta": False,
    "package_dir": PACKAGE_DIR,
    "build_strategy": invocations.ROBOT_BUILD_STRATEGY,
}
ns: Collection = invocations.create_namespace(is_meta=False)
ns.configure(configuration)
