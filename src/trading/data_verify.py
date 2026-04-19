from __future__ import annotations

import hashlib
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

import zstandard


@dataclass
class ArchiveVerificationResult:
    path: Path
    exists: bool
    sha256: str = ""
    member_count: int = 0
    top_level_entries: list[str] = field(default_factory=list)
    has_unsafe_paths: bool = False
    archive_format: str = "unknown"


def _is_unsafe_member(name: str) -> bool:
    pure = Path(name)
    return pure.is_absolute() or ".." in pure.parts


def _iter_tar_members(archive_path: Path):
    if archive_path.name.endswith((".tar.zst", ".tzst")):
        with archive_path.open("rb") as compressed:
            reader = zstandard.ZstdDecompressor().stream_reader(compressed)
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                for member in tar:
                    yield member
        return

    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar.getmembers():
            yield member


def verify_archive(path: str) -> ArchiveVerificationResult:
    archive_path = Path(path)
    result = ArchiveVerificationResult(path=archive_path, exists=archive_path.exists())

    if not archive_path.exists():
        return result

    digest = hashlib.sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    result.sha256 = digest.hexdigest()

    result.archive_format = "tar.zst" if archive_path.name.endswith((".tar.zst", ".tzst")) else "tar"

    top_levels: set[str] = set()
    unsafe = False
    member_count = 0
    for member in _iter_tar_members(archive_path):
        member_count += 1
        if member.name:
            top_levels.add(Path(member.name).parts[0])
        unsafe = unsafe or _is_unsafe_member(member.name)

    result.member_count = member_count
    result.top_level_entries = sorted(top_levels)
    result.has_unsafe_paths = unsafe

    return result
