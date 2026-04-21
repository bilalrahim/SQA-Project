import argparse
import json
import re
from pathlib import Path
from urllib import request
from urllib.error import URLError


REQUIRED_FIELDS = [
    "test_case_id",
    "requirement_id",
    "description",
    "input_data",
    "expected_output",
]

FIELD_ALIASES = {
    "test case id": "test_case_id",
    "test_case_id": "test_case_id",
    "requirement id": "requirement_id",
    "requirement_id": "requirement_id",
    "description": "description",
    "input data": "input_data",
    "input_data": "input_data",
    "expected output": "expected_output",
    "expected_output": "expected_output",
    "steps": "steps",
    "notes": "notes",
}


def load_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


def extract_json_object(raw_text):
    raw_text = raw_text.strip()

    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", raw_text, re.DOTALL)
    if fenced_match:
        raw_text = fenced_match.group(1).strip()

    decoder = json.JSONDecoder()
    for index, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(raw_text[index:])
            return candidate
        except json.JSONDecodeError:
            continue

    raise ValueError("Model output did not contain a valid JSON object")


def normalize_test_case_shape(test_case):
    if isinstance(test_case, dict):
        if set(REQUIRED_FIELDS).issubset(test_case.keys()):
            return test_case

        wrapper_keys = ["test_case", "testcase", "result", "output", "data"]
        for key in wrapper_keys:
            nested = test_case.get(key)
            if isinstance(nested, dict):
                test_case = nested
                break

        normalized = {}
        for key, value in test_case.items():
            canonical_key = FIELD_ALIASES.get(str(key).strip().lower())
            if canonical_key:
                normalized[canonical_key] = value

        if normalized:
            return normalized

    raise ValueError("Model output JSON did not match the expected test case schema")


def build_prompt(requirement, test_case_id):
    return f"""
You are generating one software verification test case for a regulatory requirement.

Return exactly one JSON object and nothing else.

Rules:
- Output valid JSON only.
- Use this exact schema:
  {{
    "test_case_id": "{test_case_id}",
    "requirement_id": "{requirement['requirement_id']}",
    "description": "...",
    "input_data": "...",
    "expected_output": "...",
    "steps": ["...", "..."],
    "notes": "..."
  }}
- Keep the test case minimal but specific.
- Ensure the description directly tests the requirement.
- Keep the same requirement_id and test_case_id values provided above.

Requirement details:
- requirement_id: {requirement['requirement_id']}
- source: {requirement['source']}
- description: {requirement['description']}
""".strip()


def run_ollama(model, prompt):
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }
    ).encode("utf-8")
    api_request = request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(api_request) as response:
            body = json.loads(response.read().decode("utf-8"))
    except URLError as error:
        raise RuntimeError(f"Failed to call Ollama API: {error}") from error

    if "response" not in body:
        raise RuntimeError(f"Unexpected Ollama API response: {body}")

    return body["response"]


def validate_test_case(test_case, requirement_id, test_case_id):
    test_case = normalize_test_case_shape(test_case)
    for field in REQUIRED_FIELDS:
        if field not in test_case or test_case[field] in (None, ""):
            test_case[field] = f"[Not provided by model for {requirement_id}]"

    test_case["test_case_id"] = test_case_id
    test_case["requirement_id"] = requirement_id

    if "steps" not in test_case:
        test_case["steps"] = []
    if "notes" not in test_case:
        test_case["notes"] = ""

    return test_case


def main():
    parser = argparse.ArgumentParser(description="Generate LLM-based test cases with an Ollama model")
    parser.add_argument("--requirements", "-r", required=True, help="Path to requirements JSON")
    parser.add_argument("--selected", "-s", required=True, help="Path to selected requirement IDs JSON")
    parser.add_argument("--output", "-o", required=True, help="Path to output JSON file")
    parser.add_argument("--model", "-m", required=True, help="Ollama model name, e.g. mistral or mistral:7b-instruct-q4_K_M")
    args = parser.parse_args()

    requirements = load_json(args.requirements)
    selected_ids = load_json(args.selected)
    requirements_by_id = {item["requirement_id"]: item for item in requirements}

    output = []
    for index, requirement_id in enumerate(selected_ids, start=1):
        if requirement_id not in requirements_by_id:
            raise KeyError(f"Selected requirement not found: {requirement_id}")

        requirement = requirements_by_id[requirement_id]
        test_case_id = f"TC-{index:03d}"
        prompt = build_prompt(requirement, test_case_id)
        raw_output = run_ollama(args.model, prompt)
        parsed = extract_json_object(raw_output)
        output.append(validate_test_case(parsed, requirement_id, test_case_id))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as handle:
        json.dump(output, handle, indent=2)

    print(f"Generated {len(output)} test cases with {args.model} -> {args.output}")


if __name__ == "__main__":
    main()