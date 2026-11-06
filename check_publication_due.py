"""Decide whether this UTC month's publication check still needs to run."""

import argparse
import datetime as dt
import json
from pathlib import Path


def check_due(record_path, *, event, today=None):
    """Manual runs always refresh; scheduled runs retry until this month succeeds."""
    if event == "workflow_dispatch":
        return True
    if event != "schedule":
        raise ValueError(f"Unsupported workflow event: {event}")
    if today is None:
        today = dt.datetime.now(dt.timezone.utc).date()
    try:
        record = json.loads(Path(record_path).read_text(encoding="utf-8"))
        last_check = dt.date.fromisoformat(record["last_successful_check"])
    except (OSError, ValueError, KeyError, TypeError):
        # A missing or invalid audit record must never suppress a needed check.
        return True
    return not (today.replace(day=1) <= last_check <= today)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", choices=("schedule", "workflow_dispatch"), required=True)
    parser.add_argument("--record", type=Path, default=Path(".github/publication-sync.json"))
    args = parser.parse_args()
    print("true" if check_due(args.record, event=args.event) else "false")


if __name__ == "__main__":
    main()
