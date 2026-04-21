from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from simple_term_menu import TerminalMenu

from src.common.analysis import Analysis
from src.common.indexer import Indexer
from src.common.paths import get_data_root
from src.common.util import package_data
from src.common.util.strings import snake_to_title
from src.exchanges import BetfairAdapter
from src.trading.data_extract import extract_archive
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
    data_root = get_data_root()
    print(f"active_data_root: {data_root}")
    print(f"data_root_exists: {'yes' if data_root.exists() else 'no'}")
    for line in run_doctor():
        print(line)


def markets(category: str | None = None, max_results: int = 5):
    """Fetch and print normalized Betfair market snapshots."""
    adapter = BetfairAdapter()
    validation = adapter.validate_credentials()

    print("\nMarkets report:\n")
    print(f"exchange: {adapter.name}")
    print(f"requested_category: {category or '(all)'}")
    print(f"max_results: {max_results}")
    print(f"auth_status: {validation.message}")

    if not validation.ok:
        print("\nUse `doctor` to review exchange readiness before retrying.\n")
        sys.exit(1)

    snapshots = adapter.list_markets(category=category, max_results=max_results)
    if not snapshots:
        print("\nNo markets returned for the current query.\n")
        return

    print("")
    for snapshot in snapshots:
        event_start = snapshot.event_start.isoformat() if snapshot.event_start else "unknown"
        print(f"[{snapshot.category}/{snapshot.subcategory}] {snapshot.market_title}")
        print(f"  market_id: {snapshot.market_id}")
        print(f"  start: {event_start}")
        print(f"  status: {snapshot.status}")
        for selection in snapshot.selections[:3]:
            probability = (
                f"{selection.implied_probability:.3f}" if selection.implied_probability is not None else "n/a"
            )
            print(
                "  - "
                f"{selection.selection_name}: "
                f"back={selection.best_back or 'n/a'} "
                f"lay={selection.best_lay or 'n/a'} "
                f"last={selection.last_traded or 'n/a'} "
                f"implied={probability}"
            )
        print("")


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


def data_extract(path: str | None = None, destination: str | None = None, prefixes: list[str] | None = None):
    """Extract selected archive prefixes into a quarantine destination."""
    if not path or not destination:
        print("Usage: uv run main.py data-extract <path-to-archive> <destination-dir> [prefix ...]")
        sys.exit(1)

    report = extract_archive(path, destination, prefixes or [])
    print("\nArchive selective extraction report:\n")
    print(f"archive_path: {report.archive_path}")
    print(f"destination: {report.destination}")
    print(f"prefixes: {', '.join(report.prefixes) if report.prefixes else '(all members)'}")
    print(f"extracted_members: {report.extracted_members}")
    print(f"skipped_members: {report.skipped_members}")
    print(f"extracted_bytes: {report.extracted_bytes}")


def main():
    if len(sys.argv) < 2:
        print("\nUsage: uv run main.py <command>")
        print("Commands: analyze, index, package, doctor, markets, paper, replay, data-verify, data-extract")
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
        category = sys.argv[2] if len(sys.argv) > 2 else None
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        markets(category=category, max_results=max_results)
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

    if command == "data-extract":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        destination = sys.argv[3] if len(sys.argv) > 3 else None
        prefixes = sys.argv[4:] if len(sys.argv) > 4 else []
        data_extract(path, destination, prefixes)
        sys.exit(0)

    print(f"Unknown command: {command}")
    print("Commands: analyze, index, package, doctor, markets, paper, replay, data-verify, data-extract")
    sys.exit(1)


if __name__ == "__main__":
    main()
