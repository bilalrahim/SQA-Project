# scripts/generate_test_cases.py
import json
import argparse

# ---------- Arguments ----------
parser = argparse.ArgumentParser(description="Generate test cases from requirements and expected structure")
parser.add_argument("--requirements", "-r", required=True, help="Input requirements JSON file")
parser.add_argument("--structure", "-s", required=True, help="Input expected structure JSON file")
parser.add_argument("--output", "-o", required=True, help="Output test cases JSON file")
args = parser.parse_args()

# ---------- Load Inputs ----------
with open(args.requirements, "r") as f:
    requirements = json.load(f)

with open(args.structure, "r") as f:
    structure = json.load(f)

# ---------- Build set of selected requirement IDs from structure ----------
selected_ids = set()
for parent, children in structure.items():
    for child in children:
        selected_ids.add(f"{parent}{child}")

# ---------- Generate Test Cases ----------
test_cases = []
tc_counter = 1

for req in requirements:
    if req["requirement_id"] in selected_ids:
        test_cases.append({
            "test_case_id": f"TC-{tc_counter:03d}",
            "requirement_id": req["requirement_id"],
            "description": f"Verify that: {req['description']}.",
            "input_data": f"CFR section {req['source']} compliance data",
            "expected_output": f"Requirement {req['requirement_id']} is satisfied"
        })
        tc_counter += 1

# ---------- Save ----------
with open(args.output, "w") as f:
    json.dump(test_cases, f, indent=2)

print(f"Generated {len(test_cases)} test cases → {args.output}")
