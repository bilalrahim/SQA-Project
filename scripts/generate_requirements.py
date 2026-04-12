# scripts/generate_requirements.py
import json
import re
import argparse

# ---------- Arguments ----------
parser = argparse.ArgumentParser(description="Generate requirement JSON from CFR Markdown")
parser.add_argument("--input", "-i", required=True, help="Input Markdown file (.md)")
parser.add_argument("--output", "-o", required=True, help="Output JSON file")
parser.add_argument("--cfr", "-c", required=True, help="CFR section (e.g., 21 CFR 117.130)")
parser.add_argument("--structure", "-s", help="Output expected structure JSON file")
parser.add_argument("--pick", "-p", type=int, default=10, help="Number of atomic rules to pick for structure")
args = parser.parse_args()

INPUT_MD = args.input
OUTPUT_JSON = args.output
CFR_SECTION = args.cfr

# ---------- Read File ----------
with open(INPUT_MD, "r") as f:
    lines = [line.strip() for line in f if line.strip()]

requirements = []
current_req = None
letter_index = 0       # sequential counter for top-level letters per parent
letter_map = {}        # maps original letter -> new letter (per parent)

# ---------- Parse ----------
for line in lines:

    # Capture REQ ID from section headers
    req_match = re.search(r"→\s*(REQ-[\d\.]+-\d+)", line)
    if req_match:
        current_req = req_match.group(1)
        letter_index = 0
        letter_map = {}
        continue

    # Capture atomic rules (lines with → LETTER or → LETTER+DIGIT)
    atomic_match = re.match(r"^(.*?)\s*→\s*([A-Z]\d*)$", line)
    if atomic_match and current_req:
        description = atomic_match.group(1).strip()
        original_suffix = atomic_match.group(2)

        # Clean description: strip leading dashes, numbering like (1), (i), (iv)
        description = re.sub(r'^[-\s]*', '', description)
        description = re.sub(r'^\([^)]*\)\s*', '', description)
        description = description.strip()

        if len(original_suffix) == 1:
            # Top-level child: auto-assign sequential letter
            new_letter = chr(ord('A') + letter_index)
            letter_index += 1
            letter_map[original_suffix] = new_letter
            suffix = new_letter
            parent = current_req
        else:
            # Sub-child: map original parent letter to reassigned letter
            orig_parent_letter = original_suffix[0]
            new_parent_letter = letter_map.get(orig_parent_letter, orig_parent_letter)
            sub_number = original_suffix[1:]
            suffix = f"{new_parent_letter}{sub_number}"
            parent = f"{current_req}{new_parent_letter}"

        requirement_id = f"{current_req}{suffix}"

        requirements.append({
            "requirement_id": requirement_id,
            "description": description,
            "source": CFR_SECTION,
            "parent": parent
        })

# ---------- Save requirements.json ----------
with open(OUTPUT_JSON, "w") as f:
    json.dump(requirements, f, indent=2)

print(f"Saved {len(requirements)} requirements → {OUTPUT_JSON}")

# ---------- Generate expected_structure.json ----------
if args.structure:
    pick = min(args.pick, len(requirements))
    # Select only top-level rules (single-letter suffix) for structure
    top_level = [r for r in requirements if len(r["requirement_id"].replace(r["parent"], "")) == 1]
    selected = top_level[:pick]

    structure = {}
    for req in selected:
        parent = req["parent"]
        child_letter = req["requirement_id"].replace(parent, "")
        if parent not in structure:
            structure[parent] = []
        if child_letter not in structure[parent]:
            structure[parent].append(child_letter)

    with open(args.structure, "w") as f:
        json.dump(structure, f, indent=2)

    print(f"Saved expected structure ({len(selected)} rules) → {args.structure}")
