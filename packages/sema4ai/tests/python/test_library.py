import os
import sys
import types
from pathlib import Path

import pytest

from RPA.Sema4AI import (
    NotOnPlatformError,
    ProjectNotFoundError,
    Sema4AI,
    Sema4AIError,
    WorkspaceFileExistsError,
    WorkspaceFileNotFoundError,
    WorkspacePathError,
)
from RPA.Sema4AI.workspace import WORKSPACE_ROOT_ENV

symlinks = pytest.mark.skipif(
    sys.platform == "win32",
    reason="creating symbolic links needs privileges on Windows",
)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.delenv(WORKSPACE_ROOT_ENV, raising=False)
    for name in ("SEMA4AI_BASE_URL", "SEMA4AI_PROJECT_ID", "SEMA4AI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "reports").mkdir()
    (workspace / "reports" / "summary.md").write_text("All matched.", encoding="utf-8")
    (workspace / "reports" / "2026").mkdir()
    (workspace / "reports" / "2026" / "q3.csv").write_text(
        "a,b\n1,2\n", encoding="utf-8"
    )
    (workspace / "notes.txt").write_text("hello", encoding="utf-8")
    (workspace / ".blockparty" / "workflows").mkdir(parents=True)
    (workspace / ".blockparty" / "workflows" / "run.workflow.json").write_text("{}")
    (workspace / ".blockparty-workspace-ready-abc").write_text("")
    return workspace


@pytest.fixture
def library(root):
    return Sema4AI(workspace_root=str(root))


@pytest.fixture
def outside(tmp_path):
    secret = tmp_path / "outside" / "secret.txt"
    secret.parent.mkdir()
    secret.write_text("do not read", encoding="utf-8")
    return secret


class TestWorkspaceRoot:
    def test_root_comes_from_the_platform_environment(self, root, monkeypatch):
        monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(root))
        library = Sema4AI()

        assert library.running_on_sema4_platform() is True
        assert Path(library.get_workspace_root()) == root.resolve()
        assert library.read_workspace_file("notes.txt") == "hello"

    def test_explicit_root_wins_over_the_environment(self, root, tmp_path, monkeypatch):
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(other))

        assert (
            Path(Sema4AI(workspace_root=str(root)).get_workspace_root())
            == root.resolve()
        )

    def test_no_root_outside_the_platform_is_a_clear_error(self, monkeypatch):
        monkeypatch.delenv(WORKSPACE_ROOT_ENV, raising=False)
        library = Sema4AI()

        assert library.running_on_sema4_platform() is False
        with pytest.raises(NotOnPlatformError, match=WORKSPACE_ROOT_ENV):
            library.list_workspace_files()

    def test_creating_the_library_does_not_need_a_workspace(self, monkeypatch):
        # Robot Framework imports libraries before a task can set anything up.
        monkeypatch.delenv(WORKSPACE_ROOT_ENV, raising=False)
        Sema4AI()

    @pytest.mark.parametrize("missing", ["does-not-exist", "notes.txt"])
    def test_root_must_be_an_existing_directory(self, root, missing):
        library = Sema4AI(workspace_root=str(root / missing))

        with pytest.raises(WorkspacePathError, match="not a directory"):
            library.get_workspace_root()

    def test_empty_environment_value_counts_as_unset(self, monkeypatch):
        monkeypatch.setenv(WORKSPACE_ROOT_ENV, "")

        assert Sema4AI().running_on_sema4_platform() is False
        with pytest.raises(NotOnPlatformError):
            Sema4AI().get_workspace_root()


class TestPathRules:
    @pytest.mark.parametrize(
        "path",
        [
            "../outside/secret.txt",
            "reports/../../outside/secret.txt",
            "reports/..",
            "..",
            "reports\\..\\..\\outside\\secret.txt",
        ],
    )
    def test_parent_segments_are_refused(self, library, outside, path):
        with pytest.raises(WorkspacePathError, match=r"'\.\.' segment"):
            library.read_workspace_file(path)

    @pytest.mark.parametrize(
        "path", ["/etc/passwd", "C:\\Windows\\win.ini", "c:/x", "\\\\host\\share\\f"]
    )
    def test_absolute_paths_are_refused(self, library, path):
        with pytest.raises(WorkspacePathError, match="absolute"):
            library.read_workspace_file(path)

    def test_absolute_path_of_a_real_outside_file_is_refused(self, library, outside):
        with pytest.raises(WorkspacePathError, match="absolute"):
            library.read_workspace_file(str(outside))

    @pytest.mark.parametrize("path", ["", "   ", None])
    def test_empty_paths_are_refused(self, library, path):
        with pytest.raises(WorkspacePathError, match="empty"):
            library.read_workspace_file(path)

    @pytest.mark.parametrize("path", [".", "./", "././."])
    def test_the_root_itself_is_not_a_file(self, library, path):
        with pytest.raises(WorkspacePathError, match="workspace root"):
            library.write_workspace_file(path, "x")

    def test_nul_character_is_refused(self, library):
        with pytest.raises(WorkspacePathError, match="NUL"):
            library.read_workspace_file("notes\x00.txt")

    def test_backslashes_and_redundant_separators_are_normalised(self, library):
        assert library.read_workspace_file("reports\\summary.md") == "All matched."
        assert library.read_workspace_file("./reports//summary.md") == "All matched."

    @symlinks
    def test_symlink_to_an_outside_file_cannot_be_read(self, library, root, outside):
        (root / "link.txt").symlink_to(outside)

        with pytest.raises(WorkspacePathError, match="outside the workspace"):
            library.read_workspace_file("link.txt")
        assert library.workspace_file_exists("notes.txt") is True

    @symlinks
    def test_symlinked_directory_cannot_be_used_to_write_outside(
        self, library, root, outside
    ):
        (root / "escape").symlink_to(outside.parent, target_is_directory=True)

        with pytest.raises(WorkspacePathError, match="outside the workspace"):
            library.write_workspace_file("escape/planted.txt", "x")
        assert not (outside.parent / "planted.txt").exists()

    @symlinks
    def test_listing_skips_links_that_leave_the_workspace(self, library, root, outside):
        (root / "reports" / "link.txt").symlink_to(outside)
        (root / "reports" / "broken.txt").symlink_to(root / "nowhere")

        paths = [entry["path"] for entry in library.list_workspace_files("reports")]

        assert paths == ["reports/summary.md", "reports/2026/q3.csv"]

    @symlinks
    def test_symlink_inside_the_workspace_is_followed(self, library, root):
        (root / "alias.txt").symlink_to(root / "notes.txt")

        assert library.read_workspace_file("alias.txt") == "hello"


class TestManagedContent:
    @pytest.mark.parametrize(
        "path",
        [
            ".blockparty/workflows/run.workflow.json",
            ".blockparty/new.json",
            ".workspace_mcp/tool.py",
            ".blockparty-workspace-ready-abc",
            "./.blockparty/workflows/run.workflow.json",
        ],
    )
    def test_writes_to_managed_areas_are_refused(self, library, root, path):
        with pytest.raises(WorkspacePathError, match="platform-managed"):
            library.write_workspace_file(path, "changed")
        assert (
            root / ".blockparty" / "workflows" / "run.workflow.json"
        ).read_text() == "{}"

    def test_managed_files_cannot_be_deleted_or_moved(self, library, root):
        managed = ".blockparty/workflows/run.workflow.json"

        with pytest.raises(WorkspacePathError, match="platform-managed"):
            library.delete_workspace_file(managed)
        with pytest.raises(WorkspacePathError, match="platform-managed"):
            library.move_workspace_file(managed, "stolen.json")
        with pytest.raises(WorkspacePathError, match="platform-managed"):
            library.move_workspace_file("notes.txt", ".blockparty/notes.txt")
        assert (root / managed).exists()
        assert (root / "notes.txt").exists()

    def test_managed_files_can_be_read(self, library):
        assert (
            library.read_workspace_file(".blockparty/workflows/run.workflow.json")
            == "{}"
        )

    def test_listing_hides_managed_content_unless_asked(self, library):
        default = [entry["path"] for entry in library.list_workspace_files()]
        everything = [
            entry["path"]
            for entry in library.list_workspace_files(include_managed=True)
        ]

        assert default == ["notes.txt", "reports/summary.md", "reports/2026/q3.csv"]
        assert ".blockparty/workflows/run.workflow.json" in everything
        assert ".blockparty-workspace-ready-abc" in everything

    def test_a_name_that_only_looks_managed_is_ordinary(self, library):
        library.write_workspace_file(".blockpartyish/file.txt", "ok")
        library.write_workspace_file("docs/.blockparty/file.txt", "ok")

        assert library.read_workspace_file("docs/.blockparty/file.txt") == "ok"

    def test_protection_can_be_switched_off(self, root):
        library = Sema4AI(workspace_root=str(root), protect_managed=False)

        library.write_workspace_file(".blockparty/project/notes.md", "ok")

        assert (root / ".blockparty" / "project" / "notes.md").read_text() == "ok"


class TestListing:
    def test_entries_describe_each_file(self, library, root):
        entry = library.list_workspace_files("reports/summary.md")[0]

        assert entry["path"] == "reports/summary.md"
        assert entry["name"] == "summary.md"
        assert entry["size"] == len("All matched.")
        assert entry["modified"].endswith("+00:00")

    def test_non_recursive_listing_stays_in_the_directory(self, library):
        paths = [
            e["path"] for e in library.list_workspace_files("reports", recursive=False)
        ]

        assert paths == ["reports/summary.md"]

    def test_empty_directory_lists_nothing(self, library, root):
        (root / "empty").mkdir()

        assert library.list_workspace_files("empty") == []

    def test_missing_prefix_is_an_error_not_an_empty_list(self, library):
        with pytest.raises(WorkspaceFileNotFoundError):
            library.list_workspace_files("no-such-dir")

    def test_paths_use_forward_slashes(self, library):
        for entry in library.list_workspace_files():
            assert "\\" not in entry["path"]


class TestReadAndWrite:
    def test_text_round_trip_with_non_ascii_content(self, library):
        text = "Lasku 1234: 12,50 €, hyväksytty ✓\n"

        assert library.write_workspace_file("out/lasku.txt", text) == "out/lasku.txt"
        assert library.read_workspace_file("out/lasku.txt") == text

    def test_binary_round_trip(self, library):
        data = bytes(range(256))

        library.write_workspace_file("out/data.bin", data)

        assert library.read_workspace_binary_file("out/data.bin") == data

    def test_bytearray_content_is_accepted(self, library):
        library.write_workspace_file("out/data.bin", bytearray(b"\x00\x01"))

        assert library.read_workspace_binary_file("out/data.bin") == b"\x00\x01"

    def test_empty_content_creates_an_empty_file(self, library, root):
        library.write_workspace_file("out/empty.txt", "")

        assert (root / "out" / "empty.txt").stat().st_size == 0

    def test_other_encodings(self, library, root):
        library.write_workspace_file("out/latin.txt", "Hänninen", encoding="latin-1")

        assert (root / "out" / "latin.txt").read_bytes() == "Hänninen".encode("latin-1")
        assert (
            library.read_workspace_file("out/latin.txt", encoding="latin-1")
            == "Hänninen"
        )

    def test_wrong_encoding_fails_instead_of_returning_garbage(self, library):
        library.write_workspace_file("out/data.bin", b"\xff\xfe\xfa")

        with pytest.raises(UnicodeDecodeError):
            library.read_workspace_file("out/data.bin")

    @pytest.mark.parametrize("content", [123, None, ["a"], {"a": 1}])
    def test_content_must_be_text_or_bytes(self, library, root, content):
        with pytest.raises(TypeError, match="text or bytes"):
            library.write_workspace_file("out/bad.txt", content)
        assert not (root / "out" / "bad.txt").exists()

    def test_overwrite_is_the_default(self, library):
        library.write_workspace_file("notes.txt", "new")

        assert library.read_workspace_file("notes.txt") == "new"

    def test_overwrite_off_keeps_the_existing_file(self, library):
        with pytest.raises(WorkspaceFileExistsError):
            library.write_workspace_file("notes.txt", "new", overwrite=False)
        assert library.read_workspace_file("notes.txt") == "hello"

    def test_a_directory_cannot_be_written_or_read_as_a_file(self, library):
        with pytest.raises(WorkspacePathError, match="directory"):
            library.write_workspace_file("reports", "x")
        with pytest.raises(WorkspacePathError, match="directory"):
            library.read_workspace_file("reports")

    def test_a_file_cannot_be_used_as_a_directory(self, library):
        with pytest.raises((NotADirectoryError, FileExistsError)):
            library.write_workspace_file("notes.txt/child.txt", "x")

    def test_missing_file(self, library):
        with pytest.raises(WorkspaceFileNotFoundError):
            library.read_workspace_file("reports/nope.md")
        with pytest.raises(FileNotFoundError):
            library.read_workspace_binary_file("reports/nope.md")
        assert library.workspace_file_exists("reports/nope.md") is False
        assert library.workspace_file_exists("reports") is False

    def test_large_file_round_trip(self, library):
        data = os.urandom(5 * 1024 * 1024)

        library.write_workspace_file("out/large.bin", data)

        assert library.read_workspace_binary_file("out/large.bin") == data


class TestMoveDeleteCopy:
    def test_move_creates_the_target_directory(self, library, root):
        assert library.move_workspace_file("notes.txt", "archive/2026/notes.txt") == (
            "archive/2026/notes.txt"
        )
        assert not (root / "notes.txt").exists()
        assert (root / "archive" / "2026" / "notes.txt").read_text() == "hello"

    def test_move_does_not_overwrite_by_default(self, library):
        with pytest.raises(WorkspaceFileExistsError):
            library.move_workspace_file("notes.txt", "reports/summary.md")
        assert library.read_workspace_file("notes.txt") == "hello"
        assert library.read_workspace_file("reports/summary.md") == "All matched."

    def test_move_can_overwrite(self, library):
        library.move_workspace_file("notes.txt", "reports/summary.md", overwrite=True)

        assert library.read_workspace_file("reports/summary.md") == "hello"

    def test_move_onto_itself_keeps_the_file(self, library):
        library.move_workspace_file("notes.txt", "./notes.txt", overwrite=True)

        assert library.read_workspace_file("notes.txt") == "hello"

    def test_move_of_a_missing_file_or_a_directory(self, library):
        with pytest.raises(WorkspaceFileNotFoundError):
            library.move_workspace_file("nope.txt", "x.txt")
        with pytest.raises(WorkspacePathError, match="directory"):
            library.move_workspace_file("reports", "moved")

    def test_move_cannot_leave_the_workspace(self, library, root):
        with pytest.raises(WorkspacePathError):
            library.move_workspace_file("notes.txt", "../notes.txt")
        assert (root / "notes.txt").exists()

    def test_delete(self, library, root):
        assert library.delete_workspace_file("notes.txt") is True
        assert not (root / "notes.txt").exists()

    def test_delete_missing(self, library):
        with pytest.raises(WorkspaceFileNotFoundError):
            library.delete_workspace_file("nope.txt")
        assert library.delete_workspace_file("nope.txt", missing_ok=True) is False

    def test_delete_never_removes_a_directory(self, library, root):
        with pytest.raises(WorkspacePathError, match="directory"):
            library.delete_workspace_file("reports")
        with pytest.raises(WorkspacePathError, match="directory"):
            library.delete_workspace_file("reports", missing_ok=True)
        assert (root / "reports" / "summary.md").exists()

    def test_copy_in_and_out(self, library, tmp_path, root):
        local = tmp_path / "report.xlsx"
        local.write_bytes(b"PK\x03\x04")

        assert library.copy_file_to_workspace(str(local), "reports/report.xlsx") == (
            "reports/report.xlsx"
        )
        copy = library.copy_file_from_workspace(
            "reports/report.xlsx", str(tmp_path / "out")
        )

        assert Path(copy).read_bytes() == b"PK\x03\x04"
        assert local.exists()

    def test_copy_out_into_a_directory_keeps_the_name(self, library, tmp_path):
        copy = library.copy_file_from_workspace("reports/summary.md", str(tmp_path))

        assert Path(copy) == (tmp_path / "summary.md").resolve()

    def test_copy_respects_overwrite_off(self, library, tmp_path):
        local = tmp_path / "notes.txt"
        local.write_text("local")

        with pytest.raises(WorkspaceFileExistsError):
            library.copy_file_to_workspace(str(local), "notes.txt", overwrite=False)
        with pytest.raises(FileExistsError):
            library.copy_file_from_workspace("notes.txt", str(local), overwrite=False)
        assert library.read_workspace_file("notes.txt") == "hello"
        assert local.read_text() == "local"

    def test_copy_of_missing_sources(self, library, tmp_path):
        with pytest.raises(FileNotFoundError):
            library.copy_file_to_workspace(str(tmp_path / "nope"), "x.txt")
        with pytest.raises(WorkspaceFileNotFoundError):
            library.copy_file_from_workspace("nope.txt", str(tmp_path))

    def test_copy_in_cannot_target_outside_or_managed_paths(self, library, tmp_path):
        local = tmp_path / "f.txt"
        local.write_text("x")

        with pytest.raises(WorkspacePathError):
            library.copy_file_to_workspace(str(local), "../f.txt")
        with pytest.raises(WorkspacePathError, match="platform-managed"):
            library.copy_file_to_workspace(str(local), ".blockparty/f.txt")


PROJECTS = [
    {
        "project_id": "1111",
        "name": "Invoices",
        "slug": "invoices",
        "kind": "project",
        "status": "active",
        "description": "Invoice processing",
    },
    {
        "project_id": "2222",
        "name": "Payroll",
        "slug": "payroll",
        "kind": "project",
        "status": "active",
        "description": "",
    },
    {
        "project_id": "3333",
        "name": "payroll",
        "slug": "payroll-2",
        "kind": "project",
        "status": "active",
        "description": "Same name, different case",
    },
    {
        "project_id": "4444",
        "name": "Old",
        "slug": "old",
        "kind": "project",
        "status": "archived",
        "description": "",
    },
]


@pytest.fixture
def platform_sdk(monkeypatch):
    calls = []

    def list_projects(*, include_archived=False):
        calls.append(include_archived)
        return [p for p in PROJECTS if include_archived or p["status"] != "archived"]

    meta = types.ModuleType("sdk.meta")
    meta.tenant = types.SimpleNamespace(list_projects=list_projects)
    sdk = types.ModuleType("sdk")
    sdk.meta = meta
    monkeypatch.setitem(sys.modules, "sdk", sdk)
    monkeypatch.setitem(sys.modules, "sdk.meta", meta)
    return calls


class TestProjects:
    def test_projects_need_the_platform_sdk(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "sdk", None)
        monkeypatch.setitem(sys.modules, "sdk.meta", None)

        with pytest.raises(NotOnPlatformError, match="platform SDK"):
            Sema4AI().list_projects()
        with pytest.raises(Sema4AIError):
            Sema4AI().get_project("Invoices")

    def test_list_projects_passes_the_archived_flag(self, platform_sdk):
        library = Sema4AI()

        assert [p["name"] for p in library.list_projects()] == [
            "Invoices",
            "Payroll",
            "payroll",
        ]
        assert len(library.list_projects(include_archived=True)) == 4
        assert platform_sdk == [False, True]

    def test_projects_are_returned_unchanged(self, platform_sdk):
        assert Sema4AI().list_projects()[0] == PROJECTS[0]

    @pytest.mark.parametrize(
        "identifier", ["1111", "invoices", "Invoices", "INVOICES", " Invoices "]
    )
    def test_get_project_by_id_slug_or_name(self, platform_sdk, identifier):
        assert Sema4AI().get_project(identifier)["project_id"] == "1111"

    def test_slug_wins_over_an_ambiguous_name(self, platform_sdk):
        # "payroll" is the slug of 2222 and, ignoring case, the name of two projects.
        assert Sema4AI().get_project("payroll")["project_id"] == "2222"

    def test_ambiguous_name_is_an_error(self, platform_sdk):
        with pytest.raises(ProjectNotFoundError, match="2 projects"):
            Sema4AI().get_project("PAYROLL")

    @pytest.mark.parametrize("identifier", ["nope", "", "   ", "111"])
    def test_unknown_project(self, platform_sdk, identifier):
        with pytest.raises(ProjectNotFoundError):
            Sema4AI().get_project(identifier)

    def test_archived_projects_are_found_only_when_asked(self, platform_sdk):
        with pytest.raises(ProjectNotFoundError):
            Sema4AI().get_project("Old")
        assert (
            Sema4AI().get_project("Old", include_archived=True)["project_id"] == "4444"
        )
