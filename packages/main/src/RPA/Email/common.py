"""Common utilities shared by any e-mail related library."""


from pathlib import Path


def counter_duplicate_path(file_path: Path) -> Path:
    """Returns a unique file path by adding a suffixed counter if already exists."""
    if not file_path.exists():
        return file_path  # unique already

    root_dir = file_path.parent
    duplicates = root_dir.glob(f"{file_path.stem}*{file_path.suffix}")
    suffixes = []
    for dup in duplicates:
        parts = dup.stem.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            suffixes.append(int(parts[1]))
    next_suffix = max(suffixes) + 1 if suffixes else 2

    file_path = root_dir / f"{file_path.stem}-{next_suffix}{file_path.suffix}"
    return file_path
