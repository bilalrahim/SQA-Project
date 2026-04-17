import argparse
import json
import logging
import re
import sys
from pathlib import Path

"""Verification script for requirements and test cases with Forensick logging."""

LOGGER = logging.getLogger("forensick.verify")
REQUIRED_FIELDS = ["requirement_id", "description", "source"]
REQ_ID_PATTERN = re.compile(r"^REQ-[A-Za-z0-9.]+-\d{3}[A-Z][A-Z0-9]*$")
VAGUE_PHRASES = {"all hazards", "etc", "and so on", "as needed", "appropriate"}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def configure_logging(log_path: Path) -> None:
    """Sets up the forensick log used by Task 4."""
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

    LOGGER.info("Verification logging initialized")


def load_json(path: Path):
    """Loads one JSON artifact and logs the action."""
    LOGGER.info("Loading JSON file: %s", path.name)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        LOGGER.info("Loaded JSON successfully: %s", path.name)
        return data
    except Exception as exc:
        LOGGER.exception("Failed to load JSON file %s: %s", path.name, exc)
        raise


def verify_required_fields(requirements: list[dict]) -> list[str]:
    """Makes sure each requirement has the fields needed for the project."""
    LOGGER.info("Running required-field verification on %d requirements", len(requirements))
    failures: list[str] = []

    for requirement in requirements:
        rid = requirement.get("requirement_id", "<missing-id>")
        for field in REQUIRED_FIELDS:
            if field not in requirement:
                failure = f"Missing field '{field}' in requirement: {rid}"
                failures.append(failure)
                LOGGER.warning(failure)

    LOGGER.info("Required-field verification complete. Failures=%d", len(failures))
    return failures


def verify_requirement_ids(requirements: list[dict]) -> list[str]:
    """Checks the ID naming pattern."""
    LOGGER.info("Running requirement ID format verification")
    failures: list[str] = []

    for requirement in requirements:
        rid = requirement.get("requirement_id", "")
        if rid and not REQ_ID_PATTERN.match(rid):
            failure = f"Invalid requirement_id format: {rid}"
            failures.append(failure)
            LOGGER.warning(failure)

    LOGGER.info("Requirement ID verification complete. Failures=%d", len(failures))
    return failures


def verify_selected_subset(expected_structure: dict, test_cases: list[dict]) -> list[str]:
    """Ensures the selected 10 atomic rules match the generated test cases."""
    LOGGER.info("Running selected-subset verification against expected_structure.json")
    failures: list[str] = []

    expected_ids = {f"{parent}{suffix}" for parent, suffixes in expected_structure.items() for suffix in suffixes}
    testcase_ids = {case.get("requirement_id", "") for case in test_cases}

    for rid in sorted(expected_ids - testcase_ids):
        failure = f"Selected requirement missing test case: {rid}"
        failures.append(failure)
        LOGGER.warning(failure)

    for rid in sorted(testcase_ids - expected_ids):
        failure = f"Unexpected test case for unselected requirement: {rid}"
        failures.append(failure)
        LOGGER.warning(failure)

    LOGGER.info(
        "Selected-subset verification complete. Expected=%d TestCases=%d Failures=%d",
        len(expected_ids),
        len(testcase_ids),
        len(failures),
    )
    return failures


def verify_requirement_test_coverage(expected_structure: dict, requirements: list[dict], test_cases: list[dict]) -> list[str]:
    """Making sure each selected requirement exists and has at least one test case."""
    LOGGER.info("Running requirement-to-test coverage verification")
    failures: list[str] = []

    expected_ids = {f"{parent}{suffix}" for parent, suffixes in expected_structure.items() for suffix in suffixes}
    actual_ids = {requirement.get("requirement_id", "") for requirement in requirements}
    test_ids = {test_case.get("requirement_id", "") for test_case in test_cases}

    for rid in sorted(expected_ids):
        if rid not in actual_ids:
            failure = f"Selected requirement missing from requirements.json: {rid}"
            failures.append(failure)
            LOGGER.warning(failure)
        if rid not in test_ids:
            failure = f"No test case for selected requirement: {rid}"
            failures.append(failure)
            LOGGER.warning(failure)

    LOGGER.info("Requirement-to-test coverage verification complete. Failures=%d", len(failures))
    return failures


def verify_description_quality(requirements: list[dict]) -> list[str]:
    """Flag vague placeholder language inside requirement descriptions."""
    LOGGER.info("Running requirement description quality verification")
    failures: list[str] = []

    for requirement in requirements:
        rid = requirement.get("requirement_id", "<missing-id>")
        description = requirement.get("description", "").lower()
        for phrase in VAGUE_PHRASES:
            if phrase in description:
                failure = f"Vague description in requirement {rid}: contains '{phrase}'"
                failures.append(failure)
                LOGGER.warning(failure)

    LOGGER.info("Description quality verification complete. Failures=%d", len(failures))
    return failures


def verify_parent_child_consistency(requirements: list[dict]) -> list[str]:
    """Check that each child requirement begins with its parent ID."""
    LOGGER.info("Running parent-child consistency verification")
    failures: list[str] = []

    for requirement in requirements:
        rid = requirement.get("requirement_id", "")
        parent = requirement.get("parent")
        if parent and rid and not rid.startswith(parent):
            failure = f"Parent-child ID mismatch: {rid} (parent {parent})"
            failures.append(failure)
            LOGGER.warning(failure)

    LOGGER.info("Parent-child consistency verification complete. Failures=%d", len(failures))
    return failures


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Verify CFR requirements and test cases.")
    parser.add_argument("--requirements", default=str(root / "requirements.json"))
    parser.add_argument("--test-cases", default=str(root / "test_cases.json"))
    parser.add_argument("--expected-structure", default=str(root / "expected_structure.json"))
    parser.add_argument("--log", default=str(root / "forensic.log"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(Path(args.log))

    requirements = load_json(Path(args.requirements))
    test_cases = load_json(Path(args.test_cases))
    expected_structure = load_json(Path(args.expected_structure))

    failures: list[str] = []
    failures.extend(verify_required_fields(requirements))
    failures.extend(verify_requirement_ids(requirements))
    failures.extend(verify_selected_subset(expected_structure, test_cases))
    failures.extend(verify_requirement_test_coverage(expected_structure, requirements, test_cases))
    failures.extend(verify_description_quality(requirements))
    failures.extend(verify_parent_child_consistency(requirements))

    if failures:
        LOGGER.error("Verification FAILED. Failure count=%d", len(failures))
        print("Verification FAILED:")
        for failure in failures:
            print("-", failure)
        return 1

    LOGGER.info("Verification passed: all requirements meet structural rules.")
    print("Verification passed: all requirements meet structural rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())