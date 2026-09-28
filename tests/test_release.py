from pathlib import Path

import pytest

from release_support import validate_release


def release_tree(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.7\n")
    notes = tmp_path / "releases" / "v0.7.md"
    notes.parent.mkdir()
    notes.write_text("# TikoPlay 0.7\n\nAutomatyczne paczki Windows i macOS.\n")
    return tmp_path


def test_release_uses_notes_for_matching_version(tmp_path):
    root = release_tree(tmp_path)
    assert validate_release(root, "v0.7") == root / "releases" / "v0.7.md"


@pytest.mark.parametrize("tag", ["v0.8", "v0.7.1", "v00.7", "v0.7-test", "../v0.7"])
def test_release_rejects_wrong_or_malformed_tag(tmp_path, tag):
    with pytest.raises(ValueError):
        validate_release(release_tree(tmp_path), tag)


@pytest.mark.parametrize("notes", [None, "", "# TikoPlay 0.7\n"])
def test_release_rejects_missing_or_heading_only_notes(tmp_path, notes):
    root = release_tree(tmp_path)
    path = root / "releases" / "v0.7.md"
    if notes is None:
        path.unlink()
    else:
        path.write_text(notes)
    with pytest.raises(ValueError):
        validate_release(root, "v0.7")
