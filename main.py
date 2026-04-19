from __future__ import annotations

import sys
from pathlib import Path

from simple_term_menu import TerminalMenu

from src.common.analysis import Analysis
from src.common.indexer import Indexer
from src.common.util import package_data
from src.common.util.strings import snake_to_title
from src.trading.data_verify import verify_archive
from src.trading.doctor import run_doctor


def analyze(name: str | None = None):
    """Run analysis by name or show interactive menu."""
    analyses = Analysis.load()

    if not analyses:
        print("No analyses found in src/analysis/")
        return

    output_dir = Path("output")

    # If name provided, run that specific analysis
    if name:
        if name == "all":
            print("\nRunning all analyses...\n")
            for analysis_cls in analyses:
                instance = analysis_cls()
                print(f"Running: {instance.name}")
                saved = instance.save(output_dir, formats=["png", "pdf", "csv", "json", "gif"])
                for fmt, path in saved.items():
                    print(f"  {fmt}: {path}")
            print("\nAll analyses complete.")
            return

        # Find matching analysis
        for analysis_cls in analyses:
            instance = analysis_cls()
            if instance.name == name:
                print(f"\nRunning: {instance.name}\n")
                saved = instance.save(output_dir, formats=["png", "pdf", "csv", "json", "gif"])
                print("Saved files:")
                for fmt, path in saved.items():
                    print(f"  {fmt}: {path}")
                return

        # No match found
        print(f"Analysis '{name}' not found. Available analyses:")
        for analysis_cls in analyses:
            instance = analysis_cls()
            print(f"  - {instance.name}")
        sys.exit(1)

    # Interactive menu mode
    options = ["[All] Run all analyses"]
    for analysis_cls in analyses:
        instance = analysis_cls()
        options.append(f"{snake_to_title(instance.name)}: {instance.description}")
    options.append("[Exit]")

    menu = TerminalMenu(
        options,
        title="Select an analysis to run (use arrow keys):",
        cycle_cursor=True,
        clear_screen=False,
    )
    choice = menu.show()

    if choice is None or choice == len(options) - 1:
        print("Exiting.")
        return

    if choice == 0:
        # Run all analyses
        print("\nRunning all analyses...\n")
        for analysis_cls in analyses:
            instance = analysis_cls()
            print(f"Running: {instance.name}")
            saved = instance.save(output_dir, formats=["png", "pdf", "csv", "json", "gif"])
            for fmt, path in saved.items():
                print(f"  {fmt}: {path}")
        print("\nAll analyses complete.")
    else:
        # Run selected analysis
        analysis_cls = analyses[choice - 1]
        instance = analysis_cls()
        print(f"\nRunning: {instance.name}\n")
        saved = instance.save(output_dir, formats=["png", "pdf", "csv", "json", "gif"])
        print("Saved files:")
        for fmt, path in saved.items():
            print(f"  {fmt}: {path}")


def index():
    """Interactive indexer selection menu."""
    indexers = Indexer.load()

    if not indexers:
        print("No indexers found in src/indexers/")
        return

    # Build menu options
    options = []
    for indexer_cls in indexers:
        instance = indexer_cls()
        options.append(f"{snake_to_title(instance.name)}: {instance.description}")
    options.append("[Exit]")

    menu = TerminalMenu(
        options,
        title="Select an indexer to run (use arrow keys):",
        cycle_cursor=True,
        clear_screen=False,
    )
    choice = menu.show()

    if choice is None or choice == len(options) - 1:
        print("Exiting.")
        return

    indexer_cls = indexers[choice]
    instance = indexer_cls()
    print(f"\nRunning: {instance.name}\n")
    instance.run()
    print("\nIndexer complete.")


def package():
    """Package the data directory into a zstd-compressed tar archive."""
    success = package_data()
    sys.exit(0 if success else 1)


def doctor():
    """Validate exchange credentials and approval readiness."""
    print("\nDoctor report:\n")
    for line in run_doctor():
        print(line)


def markets():
    """Print current market-access status."""
    print("\nMarkets command is currently a foundation command.")
    print("Use `doctor` first to confirm exchange readiness.")
    print("Normalized market polling will be layered on top of the exchange adapters next.\n")


def paper():
    """Paper-trading placeholder command for milestone one."""
    print("\nPaper mode is enabled by design.")
    print("The paper broker foundation is present, but no live exchange execution is allowed.\n")


def replay():
    """Replay placeholder command for milestone one."""
    print("\nReplay mode will use saved snapshots only.")
    print("No live exchange calls should happen in replay mode.\n")


def data_verify(path: str | None = None):
    """Compute SHA-256 and inspect an archive before extraction."""
    if not path:
        print("Usage: uv run main.py data-verify <path-to-archive>")
        sys.exit(1)

    result = verify_archive(path)
    if not result.exists:
        print(f"Archive not found: {result.path}")
        sys.exit(1)

    print("\nArchive verification report:\n")
    print(f"path: {result.path}")
    print(f"archive_format: {result.archive_format}")
    print(f"sha256: {result.sha256}")
    print(f"member_count: {result.member_count}")
    print(f"top_level_entries: {', '.join(result.top_level_entries) if result.top_level_entries else '(none)'}")
    print(f"unsafe_paths_detected: {'yes' if result.has_unsafe_paths else 'no'}")
    sys.exit(1 if result.has_unsafe_paths else 0)


def main():
    if len(sys.argv) < 2:
        print("\nUsage: uv run main.py <command>")
        print("Commands: analyze, index, package, doctor, markets, paper, replay, data-verify")
        sys.exit(0)

    command = sys.argv[1]

    if command == "analyze":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        analyze(name)
        sys.exit(0)

    if command == "index":
        index()
        sys.exit(0)

    if command == "package":
        package()
        sys.exit(0)

    if command == "doctor":
        doctor()
        sys.exit(0)

    if command == "markets":
        markets()
        sys.exit(0)

    if command == "paper":
        paper()
        sys.exit(0)

    if command == "replay":
        replay()
        sys.exit(0)

    if command == "data-verify":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        data_verify(path)
        sys.exit(0)

    print(f"Unknown command: {command}")
    print("Commands: analyze, index, package, doctor, markets, paper, replay, data-verify")
    sys.exit(1)


if __name__ == "__main__":
    main()
