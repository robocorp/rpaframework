"""A small optional task collection used only when dependencies such
as ``toml`` are not installed in the system."""
import re
from pathlib import Path

import pkg_resources
from invoke import task

REQUIREMENTS = (Path(__file__).parent / "requirements.txt").resolve()


@task(
    help={"force": "Forces reinstall of the package dependencies."}, aliases=["install"]
)
def install_invocations(ctx, force=False):
    """Installs invocation dependencies directly into the system Python
    installation used to invoke this command via Pip and the requirements.txt
    maintained in this package.
    """
    with open(REQUIREMENTS) as reqs:
        to_install = [
            line.strip("\n") for line in reqs if not re.match(r"invoke|pip", line)
        ]
        ctx.run(
            f"pip install {' '.join(to_install)}"
            f"{' --force-reinstall' if force else ''}"
        )


def check_dependancy_versions() -> bool:
    """Determines if installed packages match the requirements
    file.
    """
    with open(REQUIREMENTS) as reqs:
        try:
            pkg_resources.require(reqs)
            return True
        except pkg_resources.DistributionNotFound as e:
            print(e)
            return False
        except pkg_resources.VersionConflict as e:
            print(
                f"Version conflict detected: required: '{e.req}'; installed: '{e.dist}'"
            )
            return False
