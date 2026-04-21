import subprocess
from pathlib import Path
from typing import Optional

from src.common.paths import get_data_root


def package_data(data_dir: Optional[Path] = None, output_path: Path = Path("data.tar.zst")) -> bool:
    """Package the data directory into a zstd-compressed tar archive.

    Args:
        data_dir: Path to the data directory to compress.
        output_path: Path for the output archive.

    Returns:
        True if successful, False otherwise.
    """
    data_dir = data_dir or get_data_root()

    if not data_dir.exists():
        print(f"Error: Data directory '{data_dir}' does not exist.")
        return False

    print(f"Packaging {data_dir} -> {output_path}")
    result = subprocess.run(
        ["tar", "--zstd", "-cf", str(output_path.resolve()), data_dir.name],
        cwd=str(data_dir.parent),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False

    print(f"Successfully created {output_path}")
    return True
