import json
import re
import sys

"""
Verification script for requirements and test cases.

Rules:
1. Required fields exist (requirement_id, description, source)
2. Requirement ID format: REQ-[CATEGORY]-[3 digits][letter], e.g., REQ-HAZ-001A
3. Each requirement must have at least one test case
4. No vague phrases like "all hazards" in description
5. Parent-child ID consistency (child must start with parent ID)
"""

# Load requirements and test cases
with open("requirements.json") as f:
    requirements = json.load(f)

with open("test_cases.json") as f:
    test_cases = json.load(f)

# Set of requirement_ids referenced by test cases
test_ids = {t["requirement_id"] for t in test_cases}

failures = []

for r in requirements:
    rid = r.get("requirement_id", "")

    # Rule 1: Required fields
    for field in ["requirement_id", "description", "source"]:
        if field not in r:
            failures.append(f"Missing field '{field}' in requirement: {r}")

    # Rule 2: ID format
    if rid and not re.match(r"REQ-[A-Z]+-\d{3}[A-Z]$", rid):
        failures.append(f"Invalid requirement_id format: {rid}")

    # Rule 3: Must have at least one test case
    if rid and rid not in test_ids:
        failures.append(f"No test case for requirement: {rid}")

    # Rule 4: No vague phrase
    if "description" in r and "all hazards" in r["description"].lower():
        failures.append(f"Vague description in requirement: {rid}")

    # Rule 5: Parent-child consistency
    if "parent" in r and rid and not rid.startswith(r["parent"]):
        failures.append(f"Parent-child ID mismatch: {rid} (parent {r['parent']})")

# Output results
if failures:
    print("Verification FAILED:")
    for f in failures:
        print("-", f)
    sys.exit(1)  # Exit with failure code for GitHub Actions
else:
    print("Verification passed: all requirements meet structural rules.")
    sys.exit(0)