import argparse
import json
import logging
import sys
from pathlib import Path

"""Validation script for the selected CFR atomic rules with Forensick logging."""

LOGGER = logging.getLogger("forensick.validate")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def configure_logging(log_path: Path) -> None:
    """Sets up validation logging for Task 4."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    if LOGGER.handlers:
        for handler in list(LOGGER.handlers):
            LOGGER.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(stream_handler)

    LOGGER.info("Validation logging initialized")


def load_json(path: Path):
    """Loads one JSON artifact and records the action in the forensic log."""
    LOGGER.info("Loading JSON file: %s", path.name)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        LOGGER.info("Loaded JSON successfully: %s", path.name)
        return data
    except Exception as exc:
        LOGGER.exception("Failed to load JSON file %s: %s", path.name, exc)
        raise


def collect_expected_ids(expected_structure: dict) -> set[str]:
    """Turns parent->child suffix mappings into full atomic IDs."""
    LOGGER.info("Collecting expected requirement IDs from expected_structure.json")
    expected_ids = {f"{parent}{suffix}" for parent, suffixes in expected_structure.items() for suffix in suffixes}
    LOGGER.info("Collected %d expected atomic requirement IDs", len(expected_ids))
    return expected_ids


def validate_expected_requirements(expected_ids: set[str], actual_ids: set[str]) -> list[str]:
    """Checks whether every selected atomic rule exists in requirements.json."""
    LOGGER.info("Validating expected atomic requirements against requirements.json")
    failures: list[str] = []

    for rid in sorted(expected_ids):
        if rid not in actual_ids:
            failure = f"Missing requirement: {rid}"
            failures.append(failure)
            LOGGER.warning(failure)

    LOGGER.info("Expected-requirement validation complete. Failures=%d", len(failures))
    return failures


def validate_selected_count(expected_ids: set[str]) -> list[str]:
    """Confirm the project is validating the intended 10 selected atomic rules."""
    LOGGER.info("Validating selected atomic rule count")
    failures: list[str] = []
    if len(expected_ids) != 10:
        failure = f"Expected 10 selected atomic rules, but found {len(expected_ids)}"
        failures.append(failure)
        LOGGER.warning(failure)
    LOGGER.info("Selected-count validation complete. Failures=%d", len(failures))
    return failures


def log_unselected_atomic_rules(expected_structure: dict, actual_ids: set[str]) -> list[str]:
    """Log extra atomic rules under tracked parents without failing validation.

    In this project, expected_structure.json stores only the selected 10 rules, not the
    complete CFR section. So extra atomic rules are useful context, but they are not errors.
    """
    LOGGER.info("Logging unselected atomic rules under tracked parents")
    tracked_parents = set(expected_structure)
    extras = []

    for rid in sorted(actual_ids):
        for parent in tracked_parents:
            if rid.startswith(parent) and rid not in {f"{parent}{suffix}" for suffix in expected_structure[parent]}:
                extras.append(rid)
                LOGGER.info("Unselected atomic rule present in requirements.json: %s", rid)
                break

    LOGGER.info("Unselected-atomic logging complete. Count=%d", len(extras))
    return []


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Validate CFR expected structure.")
    parser.add_argument("--requirements", default=str(root / "requirements.json"))
    parser.add_argument("--expected-structure", default=str(root / "expected_structure.json"))
    parser.add_argument("--log", default=str(root / "forensic.log"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(Path(args.log))

    requirements = load_json(Path(args.requirements))
    expected_structure = load_json(Path(args.expected_structure))

    actual_ids = {requirement["requirement_id"] for requirement in requirements}
    expected_ids = collect_expected_ids(expected_structure)

    failures: list[str] = []
    failures.extend(validate_selected_count(expected_ids))
    failures.extend(validate_expected_requirements(expected_ids, actual_ids))
    failures.extend(log_unselected_atomic_rules(expected_structure, actual_ids))

    if failures:
        LOGGER.error("Validation FAILED. Failure count=%d", len(failures))
        print("\n".join(failures))
        return 1

    LOGGER.info("Validation passed: all selected enumerations are present.")
    print("Validation passed: all selected enumerations are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())