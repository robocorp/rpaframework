import importlib.metadata

# this should import the version from pyproject.toml
# it uses a catch-all try block in case the package is partially loaded.
try:
    __version__ = importlib.metadata.version("rpaframework")
except Exception:  # pylint: disable=broad-except
    __version__ = "0.0.0"
