from __future__ import annotations

import tarfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import zstandard as zstd


@dataclass
class ExtractReport:
    archive_path: Path
    destination: Path
    prefixes: tuple[str, ...]
    extracted_members: int
    skipped_members: int
    extracted_bytes: int


def _normalize_prefixes(prefixes: Iterable[str]) -> tuple[str, ...]:
    normalized = []
    for prefix in prefixes:
        clean = prefix.strip().strip("/")
        if not clean:
            continue
        normalized.append(clean)
    return tuple(normalized)


def _matches_prefix(member_name: str, prefixes: tuple[str, ...]) -> bool:
    if not prefixes:
        return True

    clean_name = member_name.strip("/")
    return any(clean_name == prefix or clean_name.startswith(f"{prefix}/") for prefix in prefixes)


def _is_safe_target(destination: Path, member_name: str) -> bool:
    target = destination / member_name
    try:
        target.resolve().relative_to(destination.resolve())
    except ValueError:
        return False
    return True


def extract_archive(
    archive_path: str | Path,
    destination: str | Path,
    prefixes: Iterable[str],
    skip_appledouble: bool = True,
) -> ExtractReport:
    archive = Path(archive_path).expanduser().resolve()
    output_dir = Path(destination).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_prefixes = _normalize_prefixes(prefixes)
    extracted_members = 0
    skipped_members = 0
    extracted_bytes = 0

    with archive.open("rb") as fh:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as tf:
                for member in tf:
                    if not _matches_prefix(member.name, normalized_prefixes):
                        skipped_members += 1
                        continue

                    if skip_appledouble and Path(member.name).name.startswith("._"):
                        skipped_members += 1
                        continue

                    if member.islnk() or member.issym():
                        skipped_members += 1
                        continue

                    if not _is_safe_target(output_dir, member.name):
                        raise ValueError(f"Unsafe member path during extraction: {member.name}")

                    tf.extract(member, path=output_dir, set_attrs=False)
                    extracted_members += 1
                    if member.isfile():
                        extracted_bytes += member.size

    return ExtractReport(
        archive_path=archive,
        destination=output_dir,
        prefixes=normalized_prefixes,
        extracted_members=extracted_members,
        skipped_members=skipped_members,
        extracted_bytes=extracted_bytes,
    )
