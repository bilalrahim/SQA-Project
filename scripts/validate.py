import json
import sys

# Load requirements and expected structure
with open("requirements.json") as f:
    requirements = json.load(f)

with open("expected_structure.json") as f:
    expected_structure = json.load(f)

# Build set of actual requirement IDs
actual_ids = {r["requirement_id"] for r in requirements}

failures = []

# Check all expected enumerations exist
for parent, suffixes in expected_structure.items():
    for s in suffixes:
        rid = f"{parent}{s}"
        if rid not in actual_ids:
            failures.append(f"Missing requirement: {rid}")

# Optional: check for extra/unexpected requirements
for rid in actual_ids:
    parent = rid[:11]  # REQ-HAZ-001 + A/B/C
    if parent in expected_structure:
        suffix = rid[-1]
        if suffix not in expected_structure[parent]:
            failures.append(f"Unexpected requirement: {rid}")

if failures:
    print("\n".join(failures))
    sys.exit(1)
else:
    print(" Validation passed: all enumerations complete.")
