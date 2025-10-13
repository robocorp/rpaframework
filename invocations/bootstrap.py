"""A small optional task collection used only when dependencies such
as ``toml`` are not installed in the system."""

import re
from pathlib import Path

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    import importlib_metadata
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
        f"pip install -Ur {temp_requirements}"
        f"{' --force-reinstall' if force else ''}"
    )
    # Delete the temporary requirements file
    Path(temp_requirements).unlink(missing_ok=True)


def check_dependancy_versions() -> bool:
    """Determines if installed packages match the requirements
    file.
    """
    with open(REQUIREMENTS) as reqs:
        try:
            for line in reqs:
                req = line.strip()
                if req and not req.startswith('#'):
                    # Parse requirement (simplified - just get package name)
                    pkg_name = re.split('[>=<~!]', req)[0].strip()
                    try:
                        importlib_metadata.version(pkg_name)
                    except importlib_metadata.PackageNotFoundError:
                        print(f"Package not found: {pkg_name}")
                        return False
            return True
        except Exception as e:
            print(f"Error checking dependencies: {e}")
            return False
