from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from simple_term_menu import TerminalMenu

from src.common.analysis import Analysis
from src.common.indexer import Indexer
from src.common.paths import get_data_root, get_runtime_root, runtime_path
from src.common.util import package_data
from src.common.util.strings import snake_to_title
from src.exchanges import BetfairAdapter
from src.trading.accounting import resolve_journal_position
from src.trading.data_extract import extract_archive
from src.trading.data_verify import verify_archive
from src.trading.doctor import run_doctor
from src.trading.journal import JournalStore, journal_performance_summary
from src.trading.market_history import latest_snapshot_path, load_market_snapshots, save_market_snapshots
from src.trading.paper_broker import PaperBroker
from src.trading.research import inherited_market_priors
from src.trading.strategy import StrategyDecision, strategy_for_category

load_dotenv()


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
    runtime_root = get_runtime_root()
    print(f"active_data_root: {data_root}")
    print(f"data_root_exists: {'yes' if data_root.exists() else 'no'}")
    print(f"active_runtime_root: {runtime_root}")
    print(f"runtime_root_exists: {'yes' if runtime_root.exists() else 'no'}")
    print(f"live_enabled: {os.getenv('RORY_TRADER_LIVE_ENABLED', 'false').lower()}")
    print(f"journal_path: {runtime_path('journals', 'trading_journal.jsonl')}")
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
            probability = f"{selection.implied_probability:.3f}" if selection.implied_probability is not None else "n/a"
            print(
                "  - "
                f"{selection.selection_name}: "
                f"back={selection.best_back or 'n/a'} "
                f"lay={selection.best_lay or 'n/a'} "
                f"last={selection.last_traded or 'n/a'} "
                f"implied={probability}"
            )
        print("")


def paper(category: str = "tennis", max_results: int = 50):
    """Collect snapshots, emit strategy proposals, and simulate paper fills."""
    adapter = BetfairAdapter()
    validation = adapter.validate_credentials()

    print("\nPaper report:\n")
    print(f"exchange: {adapter.name}")
    print(f"category: {category}")
    print(f"max_results: {max_results}")
    print(f"auth_status: {validation.message}")

    if not validation.ok:
        print("\nUse `doctor` to review exchange readiness before retrying.\n")
        sys.exit(1)

    captured_at = datetime.now(timezone.utc)
    snapshots = adapter.list_markets(category=category, max_results=max_results)
    for snapshot in snapshots:
        snapshot.captured_at = captured_at
        for selection in snapshot.selections:
            selection.captured_at = captured_at

    snapshot_path = save_market_snapshots(snapshots, captured_at=captured_at)
    strategy = strategy_for_category(category)
    broker = PaperBroker()
    journal = JournalStore()

    if snapshot_path is not None:
        journal.record_snapshot_collection(snapshot_path, len(snapshots), category)

    decisions = strategy.evaluate_decisions(snapshots)
    journal.record_strategy_evaluation(strategy.definition, decisions, snapshots_seen=len(snapshots))

    proposals = 0
    duplicates = 0
    paper_fills = 0

    for signal in strategy.signals_from_decisions(decisions):
        snapshot = next((item for item in snapshots if item.market_id == signal.market_id), None)
        if snapshot is None:
            continue

        proposal = journal.record_proposal(signal, snapshot)
        if proposal is None:
            duplicates += 1
            continue

        proposals += 1
        order_intent = strategy.to_order_intent(signal)
        report = broker.execute(order_intent, snapshot)
        journal.record_execution(proposal.proposal_id, report, mode="paper")
        if report.accepted:
            paper_fills += 1

    print(f"snapshot_path: {snapshot_path}")
    print(f"snapshots_collected: {len(snapshots)}")
    print(f"strategy_focus: {category}")
    print(f"strategy: {strategy.definition.name}@{strategy.definition.version}")
    print(f"strategy_decisions: {len(decisions)}")
    print(f"strategy_acceptances: {sum(1 for decision in decisions if decision.accepted)}")
    print(f"strategy_rejections: {sum(1 for decision in decisions if not decision.accepted)}")
    _print_decision_summary(decisions)
    print(f"proposals_created: {proposals}")
    print(f"duplicate_proposals_skipped: {duplicates}")
    print(f"paper_fills_created: {paper_fills}")
    print(f"journal_path: {journal.path}\n")


def replay(snapshot_path: str | None = None, output_path: str | None = None):
    """Replay a paper session from saved snapshots without live exchange calls."""
    source_path = Path(snapshot_path) if snapshot_path else latest_snapshot_path()
    if source_path is None:
        print("\nReplay failed: no saved snapshots found.\n")
        sys.exit(1)
    if not source_path.exists():
        print(f"\nReplay failed: snapshot file not found: {source_path}\n")
        sys.exit(1)

    snapshots = load_market_snapshots(source_path)
    if not snapshots:
        print(f"\nReplay failed: snapshot file contained no market rows: {source_path}\n")
        sys.exit(1)

    replay_clock = _replay_clock(source_path, snapshots)
    replay_output = (
        Path(output_path) if output_path else runtime_path("journals", "replays", f"{source_path.stem}.replay.jsonl")
    )
    if replay_output.exists():
        print(f"\nReplay failed: output journal already exists: {replay_output}\n")
        sys.exit(1)

    strategy_focus = _infer_snapshot_focus_category(snapshots)
    strategy = strategy_for_category(strategy_focus)
    broker = PaperBroker(journal_path=replay_output)
    journal = JournalStore(path=replay_output, recorded_at=replay_clock)

    replay_category = f"replay:{strategy_focus}" if strategy_focus else "replay"
    journal.record_snapshot_collection(source_path, len(snapshots), replay_category)
    decisions = strategy.evaluate_decisions(snapshots, now=replay_clock)
    journal.record_strategy_evaluation(strategy.definition, decisions, snapshots_seen=len(snapshots))

    proposals = 0
    duplicates = 0
    paper_fills = 0

    for signal in strategy.signals_from_decisions(decisions):
        snapshot = next((item for item in snapshots if item.market_id == signal.market_id), None)
        if snapshot is None:
            continue

        proposal = journal.record_proposal(signal, snapshot)
        if proposal is None:
            duplicates += 1
            continue

        proposals += 1
        order_intent = strategy.to_order_intent(signal)
        report = broker.execute(order_intent, snapshot, now=replay_clock)
        journal.record_execution(proposal.proposal_id, report, mode="paper")
        if report.accepted:
            paper_fills += 1

    print("\nReplay report:\n")
    print(f"snapshot_path: {source_path}")
    print(f"replay_clock: {replay_clock.isoformat()}")
    print(f"output_journal: {replay_output}")
    print(f"snapshots_replayed: {len(snapshots)}")
    print(f"strategy_focus: {strategy_focus or '(mixed/all)'}")
    print(f"strategy: {strategy.definition.name}@{strategy.definition.version}")
    print(f"strategy_decisions: {len(decisions)}")
    print(f"strategy_acceptances: {sum(1 for decision in decisions if decision.accepted)}")
    print(f"strategy_rejections: {sum(1 for decision in decisions if not decision.accepted)}")
    _print_decision_summary(decisions)
    print(f"proposals_created: {proposals}")
    print(f"duplicate_proposals_skipped: {duplicates}")
    print(f"paper_fills_created: {paper_fills}\n")


def _replay_clock(source_path: Path, snapshots) -> datetime:
    captured_times = [snapshot.captured_at for snapshot in snapshots if snapshot.captured_at is not None]
    if captured_times:
        clock = max(captured_times)
    else:
        clock = datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    return clock


def _infer_snapshot_focus_category(snapshots) -> str | None:
    subcategories: set[str] = set()
    categories: set[str] = set()
    for snapshot in snapshots:
        if snapshot.category:
            categories.add(snapshot.category.strip().lower())
        if snapshot.subcategory:
            subcategories.add(snapshot.subcategory.strip().lower())
        for selection in snapshot.selections:
            if selection.category:
                categories.add(selection.category.strip().lower())
            if selection.subcategory:
                subcategories.add(selection.subcategory.strip().lower())

    if subcategories == {"tennis"}:
        return "tennis"
    if len(categories) == 1:
        return next(iter(categories))
    return None


def _print_decision_summary(decisions: list[StrategyDecision]) -> None:
    rejection_counts: dict[str, int] = {}
    accepted_subcategories: dict[str, int] = {}
    decision_subcategories: dict[str, int] = {}

    for decision in decisions:
        subcategory = decision.subcategory or "unknown"
        decision_subcategories[subcategory] = decision_subcategories.get(subcategory, 0) + 1
        if decision.accepted:
            accepted_subcategories[subcategory] = accepted_subcategories.get(subcategory, 0) + 1
            continue
        rejection_counts[decision.reason_code] = rejection_counts.get(decision.reason_code, 0) + 1

    print(f"decision_subcategories: {_format_counts(decision_subcategories)}")
    print(f"accepted_subcategories: {_format_counts(accepted_subcategories)}")
    print(f"top_rejections: {_format_counts(rejection_counts)}")
    if decisions and not any(decision.accepted for decision in decisions):
        print("no_fill_summary: no accepted strategy decisions; paper broker was not invoked")


def _format_counts(counts: dict[str, int], limit: int = 5) -> str:
    if not counts:
        return "(none)"
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{key}={value}" for key, value in items)


def research_priors():
    """Summarize inherited market-behavior priors from the Becker dataset."""
    print("\nInherited market priors:\n")
    df = inherited_market_priors()
    if df.empty:
        print("No inherited priors available from the local dataset.\n")
        return

    print(f"rows: {len(df)}")
    print("")
    for _, row in df.head(12).iterrows():
        print(
            f"bucket={int(row['price_bucket_start']):02d}-{int(row['price_bucket_end']):02d}c "
            f"trades={int(row['trades'])} "
            f"implied={row['avg_implied_probability']:.3f} "
            f"actual={row['actual_win_rate']:.3f} "
            f"gap={row['calibration_gap']:+.3f}"
        )
    print("")


def journal_report():
    """Print strategy/journal performance summaries."""
    print("\nJournal report:\n")
    summary = journal_performance_summary()
    if summary["events"].empty:
        print(f"No journal events found at {runtime_path('journals', 'trading_journal.jsonl')}.\n")
        return

    overview = summary["overview"].iloc[0] if not summary["overview"].empty else None
    if overview is not None:
        print(f"journal_events: {int(overview['journal_events'])}")
        print(f"executed_positions: {int(overview['executed_positions'])}")
        print(f"open_positions: {int(overview['open_positions'])}")
        print(f"closed_positions: {int(overview['closed_positions'])}")
        print(f"won_positions: {int(overview['won_positions'])}")
        print(f"marked_open_positions: {int(overview['marked_open_positions'])}")
        print(f"total_stake: {overview['total_stake']:.2f}")
        print(f"total_commission_paid: {overview['total_commission_paid']:.2f}")
        print(f"total_realized_pnl: {overview['total_realized_pnl']:.2f}")
        print(f"total_unrealized_pnl: {overview['total_unrealized_pnl']:.2f}")
        print(f"total_net_pnl: {overview['total_net_pnl']:.2f}")
    print("")

    print("Strategy performance:")
    if summary["strategy"].empty:
        print("  (none)")
    else:
        for _, row in summary["strategy"].iterrows():
            print(
                "  "
                f"{row['strategy_name']}@{row['strategy_version']}: "
                f"executed={int(row['executed_positions'])} "
                f"open={int(row['open_positions'])} "
                f"closed={int(row['closed_positions'])} "
                f"avg_confidence={row['avg_confidence']:.3f} "
                f"total_stake={row['total_stake']:.2f} "
                f"realized={row['total_realized_pnl']:.2f} "
                f"unrealized={row['total_unrealized_pnl']:.2f}"
            )
    print("")

    print("Price bucket performance:")
    if summary["price_bucket"].empty:
        print("  (none)")
    else:
        for _, row in summary["price_bucket"].iterrows():
            print(
                "  "
                f"{row['price_bucket']}: "
                f"executed={int(row['executed_positions'])} "
                f"closed={int(row['closed_positions'])} "
                f"realized={row['total_realized_pnl']:.2f} "
                f"unrealized={row['total_unrealized_pnl']:.2f}"
            )
    print("")

    print("Time-to-event performance:")
    if summary["time_window"].empty:
        print("  (none)")
    else:
        for _, row in summary["time_window"].iterrows():
            print(
                "  "
                f"{row['time_window']}: "
                f"executed={int(row['executed_positions'])} "
                f"closed={int(row['closed_positions'])} "
                f"realized={row['total_realized_pnl']:.2f} "
                f"unrealized={row['total_unrealized_pnl']:.2f}"
            )
    print("")

    print("Open positions:")
    if summary["open_positions"].empty:
        print("  (none)")
    else:
        for _, row in summary["open_positions"].head(10).iterrows():
            mark_price = f"{row['mark_price']:.3f}" if row.get("mark_price") == row.get("mark_price") else "n/a"
            unrealized = (
                f"{row['unrealized_pnl']:.2f}" if row.get("unrealized_pnl") == row.get("unrealized_pnl") else "n/a"
            )
            print(
                "  "
                f"{row['proposal_id']} {row['selection_name']} "
                f"entry={row['fill_price']:.3f} "
                f"mark={mark_price} "
                f"unrealized={unrealized}"
            )
    print("")

    print("Closed positions:")
    if summary["closed_positions"].empty:
        print("  (none)")
    else:
        for _, row in summary["closed_positions"].head(10).iterrows():
            print(
                "  "
                f"{row['proposal_id']} {row['selection_name']} "
                f"outcome={row['resolved_outcome']} "
                f"realized={row['realized_pnl']:.2f}"
            )
    print("")

    print("Learning notes:")
    events = summary["events"]
    if events.empty or "event_type" not in events.columns:
        print("  (none)")
    else:
        learnings = events[events["event_type"] == "learning"].sort_values("recorded_at", ascending=False).head(5)
        if learnings.empty:
            print("  (none)")
        else:
            for _, row in learnings.iterrows():
                proposal_id = _display_cell(row.get("proposal_id"), default="general")
                note = _display_cell(row.get("note"), default="")
                print(f"  {proposal_id}: {note}")
    print("")


def _display_cell(value, default: str = "n/a") -> str:
    if value is None or value != value:
        return default
    return str(value)


def record_learning(proposal_id: str | None = None, note: str = ""):
    """Append a paper-trading learning note to the journal."""
    if not proposal_id or not note:
        print("Usage: uv run main.py record-learning <proposal_id|general> <note>")
        sys.exit(1)

    normalized_proposal_id = None if proposal_id in {"general", "-", "none"} else proposal_id
    try:
        JournalStore().record_learning(note, proposal_id=normalized_proposal_id, tags=["operator_learning"])
    except ValueError as exc:
        print(f"\nLearning note failed: {exc}\n")
        sys.exit(1)

    print("\nLearning note recorded:\n")
    print(f"proposal_id: {normalized_proposal_id or 'general'}")
    print(f"journal_path: {runtime_path('journals', 'trading_journal.jsonl')}\n")


def resolve_paper(proposal_id: str | None = None, outcome: str | None = None, note: str = ""):
    """Resolve an executed paper position manually and append the outcome to the journal."""
    if not proposal_id or not outcome:
        print("Usage: uv run main.py resolve-paper <proposal_id> <won|lost|void> [note]")
        sys.exit(1)

    try:
        result = resolve_journal_position(proposal_id, outcome, note=note)
    except ValueError as exc:
        print(f"\nResolution failed: {exc}\n")
        sys.exit(1)

    print("\nPaper resolution recorded:\n")
    print(f"proposal_id: {result['proposal_id']}")
    print(f"strategy: {result['strategy_name']}@{result['strategy_version']}")
    print(f"market: {result['market_title']}")
    print(f"selection: {result['selection_name']}")
    print(f"outcome: {result['resolved_outcome']}")
    print(f"realized_pnl: {result['realized_pnl']:.2f}")
    print(f"journal_path: {runtime_path('journals', 'trading_journal.jsonl')}\n")


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


def dashboard_api(host: str = "127.0.0.1", port: int = 8000):
    """Run the local/VPS dashboard API."""
    import uvicorn

    uvicorn.run("src.dashboard.api:app", host=host, port=port)


def main():
    if len(sys.argv) < 2:
        print("\nUsage: uv run main.py <command>")
        print(
            "Commands: analyze, index, package, doctor, markets, paper, replay, "
            "data-verify, data-extract, research-priors, journal-report, resolve-paper, record-learning, dashboard-api"
        )
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
        category = sys.argv[2] if len(sys.argv) > 2 else "tennis"
        max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        paper(category=category, max_results=max_results)
        sys.exit(0)

    if command == "replay":
        snapshot_path = sys.argv[2] if len(sys.argv) > 2 else None
        output_path = sys.argv[3] if len(sys.argv) > 3 else None
        replay(snapshot_path=snapshot_path, output_path=output_path)
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

    if command == "research-priors":
        research_priors()
        sys.exit(0)

    if command == "journal-report":
        journal_report()
        sys.exit(0)

    if command == "resolve-paper":
        proposal_id = sys.argv[2] if len(sys.argv) > 2 else None
        outcome = sys.argv[3] if len(sys.argv) > 3 else None
        note = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        resolve_paper(proposal_id, outcome, note)
        sys.exit(0)

    if command == "record-learning":
        proposal_id = sys.argv[2] if len(sys.argv) > 2 else None
        note = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        record_learning(proposal_id, note)
        sys.exit(0)

    if command == "dashboard-api":
        host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
        dashboard_api(host=host, port=port)
        sys.exit(0)

    print(f"Unknown command: {command}")
    print(
        "Commands: analyze, index, package, doctor, markets, paper, replay, "
        "data-verify, data-extract, research-priors, journal-report, resolve-paper, dashboard-api"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
