import tarfile
import zipfile

import pytest
from RPA.Archive import Archive


@pytest.fixture
def lib():
    return Archive()


def _make_traversal_zip(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("../evil_zip.txt", "pwned")
    return path


def _make_traversal_tar(path):
    with tarfile.open(path, "w") as tf:
        info = tarfile.TarInfo(name="../evil_tar.txt")
        data = b"pwned"
        info.size = len(data)
        import io

        tf.addfile(info, io.BytesIO(data))
    return path


def test_extract_archive_rejects_zip_slip(lib, tmp_path):
    archive = _make_traversal_zip(tmp_path / "evil.zip")
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    with pytest.raises(ValueError):
        lib.extract_archive(str(archive), str(extract_dir))

    assert not (tmp_path / "evil_zip.txt").exists()


def test_extract_archive_rejects_tar_slip(lib, tmp_path):
    archive = _make_traversal_tar(tmp_path / "evil.tar")
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    with pytest.raises(ValueError):
        lib.extract_archive(str(archive), str(extract_dir))

    assert not (tmp_path / "evil_tar.txt").exists()


def test_extract_archive_allows_normal_zip(lib, tmp_path):
    archive = tmp_path / "ok.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("hello.txt", "hi")
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    lib.extract_archive(str(archive), str(extract_dir))

    assert (extract_dir / "hello.txt").read_text() == "hi"
