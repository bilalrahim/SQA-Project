import argparse
import json
import re


REQUIRED_FIELDS = [
    "test_case_id",
    "requirement_id",
    "description",
    "input_data",
    "expected_output",
]


def load_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


def normalize_words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def completeness_check(test_case):
    missing = [field for field in REQUIRED_FIELDS if field not in test_case or test_case[field] in (None, "", [])]
    optional_useful = bool(test_case.get("steps")) or bool(str(test_case.get("notes", "")).strip())
    return {
        "has_all_required_fields": not missing,
        "missing_required_fields": missing,
        "optional_fields_useful": optional_useful,
    }


def correctness_check(test_case, requirement):
    requirement_words = normalize_words(requirement["description"])
    description_words = normalize_words(test_case.get("description", ""))
    overlap = sorted(requirement_words & description_words)
    return {
        "heuristic_match": len(overlap) >= max(2, min(4, len(requirement_words))),
        "overlap_terms": overlap,
        "manual_review_needed": True,
        "review_note": "Confirm manually that the test case actually tests the exact requirement intent.",
    }


def map_by_requirement(test_cases):
    return {item["requirement_id"]: item for item in test_cases}


def main():
    parser = argparse.ArgumentParser(description="Compare two LLM-generated test case files")
    parser.add_argument("--requirements", "-r", required=True, help="Path to requirements JSON")
    parser.add_argument("--selected", "-s", required=True, help="Path to selected requirement IDs JSON")
    parser.add_argument("--model-a-file", required=True, help="Path to model A output JSON")
    parser.add_argument("--model-a-name", required=True, help="Display name for model A")
    parser.add_argument("--model-b-file", required=True, help="Path to model B output JSON")
    parser.add_argument("--model-b-name", required=True, help="Display name for model B")
    parser.add_argument("--output", "-o", required=True, help="Path to output comparison report JSON")
    args = parser.parse_args()

    requirements = load_json(args.requirements)
    selected_ids = load_json(args.selected)
    requirements_by_id = {item["requirement_id"]: item for item in requirements}
    model_a = map_by_requirement(load_json(args.model_a_file))
    model_b = map_by_requirement(load_json(args.model_b_file))

    per_requirement = []
    coverage_count = 0
    completeness_all = True

    for requirement_id in selected_ids:
        requirement = requirements_by_id[requirement_id]
        case_a = model_a.get(requirement_id)
        case_b = model_b.get(requirement_id)
        coverage = bool(case_a) and bool(case_b)
        if coverage:
            coverage_count += 1

        completeness_a = completeness_check(case_a) if case_a else None
        completeness_b = completeness_check(case_b) if case_b else None
        correctness_a = correctness_check(case_a, requirement) if case_a else None
        correctness_b = correctness_check(case_b, requirement) if case_b else None

        if completeness_a and not completeness_a["has_all_required_fields"]:
            completeness_all = False
        if completeness_b and not completeness_b["has_all_required_fields"]:
            completeness_all = False
        if case_a is None or case_b is None:
            completeness_all = False

        per_requirement.append(
            {
                "requirement_id": requirement_id,
                "requirement_description": requirement["description"],
                "coverage": {
                    args.model_a_name: bool(case_a),
                    args.model_b_name: bool(case_b),
                    "both_models_covered": coverage,
                },
                "correctness": {
                    args.model_a_name: correctness_a,
                    args.model_b_name: correctness_b,
                },
                "completeness": {
                    args.model_a_name: completeness_a,
                    args.model_b_name: completeness_b,
                },
            }
        )

    report = {
        "summary": {
            "selected_requirements": len(selected_ids),
            "requirements_covered_by_both_models": coverage_count,
            "full_coverage": coverage_count == len(selected_ids),
            "all_required_fields_present": completeness_all,
            "correctness_requires_manual_review": True,
        },
        "models": {
            "model_a": args.model_a_name,
            "model_b": args.model_b_name,
        },
        "per_requirement": per_requirement,
    }

    with open(args.output, "w") as handle:
        json.dump(report, handle, indent=2)

    print(f"Saved comparison report -> {args.output}")


if __name__ == "__main__":
    main()