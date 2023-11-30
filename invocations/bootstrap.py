"""A small optional task collection used only when dependencies such
as ``toml`` are not installed in the system."""
import re
from pathlib import Path

import pkg_resources
from invoke import task
import tempfile

REQUIREMENTS = (Path(__file__).parent / "requirements.txt").resolve()


def create_temp_requirements():
    """Creates a temporary requirements file without 'invoke' and 'pip'."""
    with open(REQUIREMENTS) as reqs:
        temp_reqs = tempfile.NamedTemporaryFile(mode="w", delete=False)
        for line in reqs:
            if "invoke" not in line.lower() and "pip" not in line.lower():
                temp_reqs.write(line)
        temp_reqs.close()
        return temp_reqs.name


@task(
    help={"force": "Forces reinstall of the package dependencies."}, aliases=["install"]
)
def install_invocations(ctx, force=False):
    """Installs invocation dependencies directly into the system Python
    installation used to invoke this command via Pip and the temporary requirements.txt
    file without 'invoke' and 'pip'.
    """
    temp_requirements = create_temp_requirements()
    ctx.run(
        f"pip install -r {temp_requirements}" f"{' --force-reinstall' if force else ''}"
    )
    # Delete the temporary requirements file
    Path(temp_requirements).unlink(missing_ok=True)


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
