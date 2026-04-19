from __future__ import annotations

import hashlib
import tarfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArchiveVerificationResult:
    path: Path
    exists: bool
    sha256: str = ""
    member_count: int = 0
    top_level_entries: list[str] = field(default_factory=list)
    has_unsafe_paths: bool = False


def _is_unsafe_member(name: str) -> bool:
    pure = Path(name)
    return pure.is_absolute() or ".." in pure.parts


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

    tar_mode = "r:*"
    with tarfile.open(archive_path, tar_mode) as tar:
        members = tar.getmembers()
        result.member_count = len(members)
        top_levels = sorted({Path(member.name).parts[0] for member in members if member.name})
        result.top_level_entries = top_levels
        result.has_unsafe_paths = any(_is_unsafe_member(member.name) for member in members)

    return result
