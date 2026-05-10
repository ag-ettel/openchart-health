"""
Apply human review decisions to the ownership clusters CSV.

Reads YOUR_ACTION column from review_entity_classifications.csv and
modifies ownership_clusters_review.csv accordingly:

  KEEP     — no change (entity stays in its current cluster)
  REMOVE   — delete the row (entity becomes unclustered)
  MOVE_TO:xxx — change parent_group_id to xxx (move to different/new group)

Also applies display name fixes from the review sheet: if parent_group_name
differs between the review sheet and the master CSV for a given cluster,
the review sheet wins.

Usage:
    python scripts/apply_review_decisions.py [--dry-run]

Options:
    --dry-run   Show what would change without modifying files
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MASTER_CSV = Path("data/ownership_clusters_review.csv")
REVIEW_CSV = Path("data/review_entity_classifications.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply review decisions to ownership clusters CSV."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without writing")
    args = parser.parse_args()

    # Load review decisions
    with open(REVIEW_CSV, encoding="utf-8") as f:
        review_rows = list(csv.DictReader(f))

    decisions: dict[str, dict] = {}
    for r in review_rows:
        action = (r.get("YOUR_ACTION") or "").strip().upper()
        if action:
            decisions[r["entity_name"]] = {
                "action": action,
                "classification": (r.get("YOUR_CLASSIFICATION") or "").strip(),
                "notes": (r.get("YOUR_NOTES") or "").strip(),
            }

    if not decisions:
        logger.warning("No decisions found in YOUR_ACTION column. Nothing to apply.")
        logger.info("Fill in the YOUR_ACTION column in %s first.", REVIEW_CSV)
        return

    # Count actions
    action_counts = defaultdict(int)
    for d in decisions.values():
        action = d["action"]
        if action.startswith("MOVE_TO:"):
            action_counts["MOVE_TO"] += 1
        else:
            action_counts[action] += 1

    logger.info("Decisions found: %s", dict(action_counts))

    # Load master CSV
    with open(MASTER_CSV, encoding="utf-8") as f:
        master_rows = list(csv.DictReader(f))
    fieldnames = list(master_rows[0].keys())

    original_count = len(master_rows)
    kept: list[dict] = []
    removed = 0
    moved = 0
    unchanged = 0

    for row in master_rows:
        entity = row["entity_name"]
        decision = decisions.get(entity)

        if not decision:
            kept.append(row)
            unchanged += 1
            continue

        action = decision["action"]

        if action == "KEEP":
            kept.append(row)
            unchanged += 1

        elif action == "REMOVE":
            removed += 1
            if args.dry_run:
                logger.info("  REMOVE: %s (was in %s)", entity, row["parent_group_id"])

        elif action.startswith("MOVE_TO:"):
            new_group_id = action.split(":", 1)[1].strip().lower()
            old_group = row["parent_group_id"]
            row["parent_group_id"] = new_group_id
            # Use the new group ID as display name if no existing name
            # (reviewer can fix display names in a separate pass)
            if new_group_id != old_group:
                # Check if any existing row has this group ID for the display name
                existing_name = None
                for other in master_rows:
                    if other["parent_group_id"] == new_group_id:
                        existing_name = other["parent_group_name"]
                        break
                if existing_name:
                    row["parent_group_name"] = existing_name
                else:
                    # Create display name from slug
                    row["parent_group_name"] = new_group_id.replace("_", " ").title()

            kept.append(row)
            moved += 1
            if args.dry_run:
                logger.info("  MOVE: %s  %s -> %s", entity, old_group, new_group_id)

        else:
            logger.warning("Unknown action '%s' for entity '%s'. Keeping unchanged.",
                           action, entity)
            kept.append(row)
            unchanged += 1

    logger.info("")
    logger.info("Results:")
    logger.info("  Original rows:  %d", original_count)
    logger.info("  Kept unchanged: %d", unchanged)
    logger.info("  Removed:        %d", removed)
    logger.info("  Moved:          %d", moved)
    logger.info("  Final rows:     %d", len(kept))

    if args.dry_run:
        logger.info("")
        logger.info("DRY RUN — no files modified. Remove --dry-run to apply.")
        return

    # Write back
    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    logger.info("Wrote %s with %d rows", MASTER_CSV, len(kept))
    logger.info("")
    logger.info("Next steps:")
    logger.info("  python scripts/classify_ownership_structures.py")
    logger.info("  python scripts/load_ownership_groups.py --mark-verified")
    logger.info("  python scripts/classify_ownership_structures.py --write-db")


if __name__ == "__main__":
    main()
