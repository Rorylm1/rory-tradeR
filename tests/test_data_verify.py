import tarfile
from pathlib import Path

from src.trading.data_verify import verify_archive


def test_verify_archive_reports_hash_and_top_level_entries(tmp_path: Path):
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "file.txt").write_text("hello")

    archive_path = tmp_path / "payload.tar"
    with tarfile.open(archive_path, "w") as tar:
        tar.add(payload_dir, arcname="payload")

    result = verify_archive(str(archive_path))

    assert result.exists is True
    assert result.sha256
    assert result.member_count > 0
    assert result.top_level_entries == ["payload"]
    assert result.has_unsafe_paths is False


def test_verify_archive_detects_unsafe_paths(tmp_path: Path):
    archive_path = tmp_path / "unsafe.tar"
    with tarfile.open(archive_path, "w") as tar:
        member = tarfile.TarInfo("../escape.txt")
        member.size = 0
        tar.addfile(member)

    result = verify_archive(str(archive_path))

    assert result.exists is True
    assert result.has_unsafe_paths is True
