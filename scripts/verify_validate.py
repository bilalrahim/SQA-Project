import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# To run locally run:
# python scripts/verify_validate.py \
#  --requirements requirements.json \
#  --structure expected_structure.json \
#  --test-cases test_cases.json \
#  --output vv_report.json \
#  --log forensic.log
#
# make sure you are in root_dir

LOGGER = logging.getLogger("forensick")
REQUIRED_TEST_CASE_FIELDS = [
    "test_case_id",
    "requirement_id",
    "description",
    "input_data",
    "expected_output",
]

# creates log folder if needed, use INFO-level logging
def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    LOGGER.info("Forensick logging initialized")

# loads, opens, parses, and returns parsed json data.
def load_json(path: Path):
    LOGGER.info("Loading JSON file: %s", path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    LOGGER.info("Loaded JSON successfully: %s", path)
    return data

# turns requirements into a dictionary
def build_requirement_lookup(requirements):
    LOGGER.info("Building requirement lookup from requirements.json")
    lookup = {req["requirement_id"]: req for req in requirements}
    LOGGER.info("Indexed %d requirements", len(lookup))
    return lookup

# reads expected_structure.json and turns it into atomic requirement IDs.
def collect_selected_requirement_ids(structure: dict):
    LOGGER.info("Collecting selected requirement IDs from expected_structure.json")
    selected_ids = []
    for parent, children in structure.items():
        for child in children:
            selected_ids.append(f"{parent}{child}")
    LOGGER.info("Collected %d selected requirement IDs", len(selected_ids))
    return selected_ids

# verifies there are 10 selected atomic rules, no duplicates, 
# requirement IDs actually exist, each parent has a non-empty child list
def verify_selected_requirements(requirement_lookup, structure):
    LOGGER.info("Starting verification of selected structure entries")
    selected_ids = collect_selected_requirement_ids(structure)
    counter = Counter(selected_ids)
    duplicate_ids = sorted(req_id for req_id, count in counter.items() if count > 1)
    missing_ids = sorted(req_id for req_id in selected_ids if req_id not in requirement_lookup)

    invalid_children = []
    for parent, children in structure.items():
        if not isinstance(children, list) or not children:
            invalid_children.append({"parent": parent, "issue": "Child list is empty or invalid"})
            continue
        for child in children:
            if not isinstance(child, str) or not child.strip():
                invalid_children.append({"parent": parent, "issue": f"Invalid child value: {child!r}"})

    result = {
        "selected_requirement_count": len(selected_ids),
        "expected_selected_requirement_count": 10,
        "count_matches_expected": len(selected_ids) == 10,
        "duplicate_selected_requirement_ids": duplicate_ids,
        "missing_selected_requirement_ids": missing_ids,
        "invalid_structure_entries": invalid_children,
        "passed": not duplicate_ids and not missing_ids and not invalid_children and len(selected_ids) == 10,
    }
    LOGGER.info("Finished structure verification. Passed=%s", result["passed"])
    return result, selected_ids

# checks whether test_cases.json is properly mapped to selected requirements
def verify_test_case_completeness(test_cases, selected_ids):
    LOGGER.info("Verifying test case completeness and coverage")
    seen_ids = Counter(tc.get("test_case_id") for tc in test_cases)
    duplicate_test_case_ids = sorted(tc_id for tc_id, count in seen_ids.items() if tc_id and count > 1)

    missing_fields = []
    test_cases_by_requirement = {}

    for test_case in test_cases:
        req_id = test_case.get("requirement_id")
        if req_id:
            test_cases_by_requirement.setdefault(req_id, []).append(test_case.get("test_case_id", "<missing-id>"))

        missing = [field for field in REQUIRED_TEST_CASE_FIELDS if not str(test_case.get(field, "")).strip()]
        if missing:
            missing_fields.append(
                {
                    "test_case_id": test_case.get("test_case_id", "<missing-id>"),
                    "missing_fields": missing,
                }
            )

    missing_test_cases = sorted(req_id for req_id in selected_ids if req_id not in test_cases_by_requirement)
    unexpected_test_cases = sorted(req_id for req_id in test_cases_by_requirement if req_id not in selected_ids)
    multi_mapped_requirements = {
        req_id: tc_ids
        for req_id, tc_ids in sorted(test_cases_by_requirement.items())
        if len(tc_ids) > 1
    }

    result = {
        "generated_test_case_count": len(test_cases),
        "expected_test_case_count": len(selected_ids),
        "count_matches_selected_rules": len(test_cases) == len(selected_ids),
        "duplicate_test_case_ids": duplicate_test_case_ids,
        "missing_required_fields": missing_fields,
        "missing_test_cases_for_requirements": missing_test_cases,
        "unexpected_test_cases": unexpected_test_cases,
        "multiple_test_cases_for_same_requirement": multi_mapped_requirements,
        "passed": not duplicate_test_case_ids and not missing_fields and not missing_test_cases and not unexpected_test_cases and not multi_mapped_requirements and len(test_cases) == len(selected_ids),
    }
    LOGGER.info("Finished test case verification. Passed=%s", result["passed"])
    return result

# uses heuristic-based validation, so not perfect semantic analysis
def validate_test_case_alignment(test_cases, requirement_lookup):
    LOGGER.info("Starting validation of test case text against requirement descriptions")
    per_test_case = []
    failed_cases = []

    for test_case in test_cases:
        req_id = test_case.get("requirement_id", "")
        requirement = requirement_lookup.get(req_id)
        if requirement is None:
            issue = {
                "test_case_id": test_case.get("test_case_id", "<missing-id>"),
                "requirement_id": req_id,
                "issue": "Requirement ID not found in requirements.json",
            }
            per_test_case.append(issue)
            failed_cases.append(issue)
            LOGGER.warning("Validation failed for %s: unknown requirement", test_case.get("test_case_id"))
            continue

        requirement_desc = requirement["description"].strip().lower()
        description = str(test_case.get("description", "")).strip().lower()
        expected_output = str(test_case.get("expected_output", "")).strip().lower()
        input_data = str(test_case.get("input_data", "")).strip().lower()

        description_matches = requirement_desc in description or description in requirement_desc
        output_mentions_requirement = req_id.lower() in expected_output
        input_mentions_source = requirement["source"].lower() in input_data or "compliance" in input_data

        case_result = {
            "test_case_id": test_case.get("test_case_id", "<missing-id>"),
            "requirement_id": req_id,
            "description_matches_requirement": description_matches,
            "expected_output_mentions_requirement": output_mentions_requirement,
            "input_data_looks_relevant": input_mentions_source,
            "passed": description_matches and output_mentions_requirement and input_mentions_source,
        }
        per_test_case.append(case_result)

        if not case_result["passed"]:
            failed_cases.append(case_result)
            LOGGER.warning("Validation heuristic failed for %s", case_result["test_case_id"])

    result = {
        "checked_test_cases": len(test_cases),
        "failed_cases": failed_cases,
        "per_test_case": per_test_case,
        "passed": not failed_cases,
        "note": "Validation is heuristic-based. It checks whether each test case text still lines up with the selected requirement.",
    }
    LOGGER.info("Finished validation checks. Passed=%s", result["passed"])
    return result

# write the final report to vv_report.json
def write_report(report, output_path: Path):
    LOGGER.info("Writing V&V report to %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    LOGGER.info("Saved V&V report successfully")


def main():
    parser = argparse.ArgumentParser(description="Verify and validate CFR project JSON artifacts")
    parser.add_argument("--requirements", "-r", required=True, help="Path to requirements.json")
    parser.add_argument("--structure", "-s", required=True, help="Path to expected_structure.json")
    parser.add_argument("--test-cases", "-t", required=True, help="Path to test_cases.json")
    parser.add_argument("--output", "-o", default="vv_report.json", help="Output JSON report path")
    parser.add_argument("--log", "-l", default="forensick.log", help="Forensic log output path")
    args = parser.parse_args()

    configure_logging(Path(args.log))

    requirements = load_json(Path(args.requirements))
    structure = load_json(Path(args.structure))
    test_cases = load_json(Path(args.test_cases))

    requirement_lookup = build_requirement_lookup(requirements)
    structure_report, selected_ids = verify_selected_requirements(requirement_lookup, structure)
    test_case_verification = verify_test_case_completeness(test_cases, selected_ids)
    validation_report = validate_test_case_alignment(test_cases, requirement_lookup)

    verification_passed = structure_report["passed"] and test_case_verification["passed"]
    validation_passed = validation_report["passed"]
    overall_passed = verification_passed and validation_passed

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "verification_passed": verification_passed,
            "validation_passed": validation_passed,
            "overall_passed": overall_passed,
        },
        "verification": {
            "selected_requirements": structure_report,
            "test_case_integrity": test_case_verification,
        },
        "validation": validation_report,
        "forensick_integration": {
            "logged_methods": [
                "configure_logging",
                "load_json",
                "build_requirement_lookup",
                "verify_selected_requirements",
                "verify_test_case_completeness",
                "validate_test_case_alignment",
                "write_report",
            ],
            "log_file": str(args.log),
        },
    }

    write_report(report, Path(args.output))

    LOGGER.info(
        "Verification passed=%s | Validation passed=%s | Overall passed=%s",
        verification_passed,
        validation_passed,
        overall_passed,
    )

    print(json.dumps(report["summary"], indent=2))

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
