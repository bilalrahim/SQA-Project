# SQA-Project — V&V of 21 CFR Atomic Rules

Verification & Validation pipeline for regulatory requirements extracted from **21 CFR §117.130 (Hazard Analysis)**. Parses CFR Markdown into atomic requirements, generates minimal test cases, runs V&V with forensic logging, and ships a CI workflow. An individual component compares LLM-generated test cases (Mistral vs quantized Mistral).

## Objectives

- Extract atomic regulatory rules from a CFR Markdown source into structured JSON.
- Generate minimal test cases mapped to selected requirements.
- Run automated verification and validation with forensic logging.
- Automate the pipeline via GitHub Actions.
- (Individual) Compare LLM-generated test cases across two Mistral variants.

## Repository Layout

```
Input CFR File/        # Source CFR Markdown
scripts/               # All Python scripts (generate, verify, validate, LLM, reports)
sample outputs/        # Reference outputs
.github/workflows/     # CI pipeline
```

Generated at runtime: `requirements.json`, `expected_structure.json`, `test_cases.json`, `forensic.log`, `vv_report.json`, `individual_outputs/`.

## Prerequisites

- Python **3.11+**
- Git
- (Individual task only) [Ollama](https://ollama.com) with `mistral:latest` and `mistral:7b-instruct-q2_K`

## Reproduce Locally

### macOS / Linux

```bash
git clone https://github.com/bilalrahim/SQA-Project.git
cd SQA-Project

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt 2>/dev/null || pip install python-docx

# Task 1: parse CFR -> requirements + expected structure
python scripts/generate_requirements.py \
  -i "Input CFR File/CFR-117.130.md" \
  -o requirements.json \
  -c "21 CFR 117.130" \
  -s expected_structure.json -p 10

# Task 2: generate minimal test cases
python scripts/generate_test_cases.py \
  -r requirements.json -s expected_structure.json -o test_cases.json

# Tasks 3 & 4: V&V with forensic logging
python scripts/verify.py
python scripts/validate.py
```

### Windows (PowerShell)

```powershell
git clone https://github.com/bilalrahim/SQA-Project.git
cd SQA-Project

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install python-docx

python scripts\generate_requirements.py `
  -i "Input CFR File/CFR-117.130.md" `
  -o requirements.json `
  -c "21 CFR 117.130" `
  -s expected_structure.json -p 10

python scripts\generate_test_cases.py -r requirements.json -s expected_structure.json -o test_cases.json
python scripts\verify.py
python scripts\validate.py
```

### Individual LLM Task (optional)

```bash
ollama pull mistral
ollama pull mistral:7b-instruct-q2_K

python scripts/generate_llm_test_cases.py \
  -r requirements.json -s selected_rules_individual.json \
  -o individual_outputs/mistral_test_cases.json -m mistral:latest

python scripts/generate_llm_test_cases.py \
  -r requirements.json -s selected_rules_individual.json \
  -o individual_outputs/mistral_q2k_test_cases.json -m mistral:7b-instruct-q2_K

python scripts/compare_llm_outputs.py \
  -r requirements.json -s selected_rules_individual.json \
  --model-a-file individual_outputs/mistral_test_cases.json --model-a-name mistral_Q4_K_M \
  --model-b-file individual_outputs/mistral_q2k_test_cases.json --model-b-name mistral_Q2_K \
  -o individual_outputs/final_comparison_report.json
```

## Continuous Integration

Every push and PR to `main` triggers the [V&V Pipeline](.github/workflows/vv_pipeline.yml), which regenerates artifacts, runs verification + validation, and uploads `forensic.log` and `vv_report.json` as artifacts.

## Outputs

| File | Purpose |
|---|---|
| `requirements.json` | Atomic requirements parsed from CFR |
| `expected_structure.json` | Parent → child mapping for 10 selected rules |
| `test_cases.json` | One minimal test case per selected requirement |
| `forensic.log` | Forensic execution log (Task 4) |
| `vv_report.json` | Verification & validation report |

## Team

- Bilal Rahim
- Chris Bottcher

## Course

SQA 2026 — Auburn University. Deadline: April 24, 2026.
