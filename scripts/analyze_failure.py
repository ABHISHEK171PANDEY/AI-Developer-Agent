#!/usr/bin/env python3
"""
analyze_failure.py
Reads CI/CD logs, extracts errors, sends to Gemini API, and saves the fix.
"""

import argparse
import json
import os
import sys
import re
import google.generativeai as genai


def load_log(log_path: str) -> str:
    """Read the CI failure log and return its content."""
    if not os.path.exists(log_path):
        print(f"[ERROR] Log file not found: {log_path}")
        sys.exit(1)
    with open(log_path) as f:
        return f.read()


def load_source(source_path: str) -> str:
    """Read the source file that needs fixing."""
    if not os.path.exists(source_path):
        print(f"[ERROR] Source file not found: {source_path}")
        sys.exit(1)
    with open(source_path) as f:
        return f.read()


def extract_relevant_errors(log: str) -> str:
    """
    Pull out the most useful lines from CI logs:
    FAILED lines, assertion errors, flake8 codes, tracebacks.
    Keeps the payload to Gemini concise.
    """
    useful_lines = []
    capture = False

    for line in log.splitlines():
        # flake8 violations
        if re.search(r'\s[EWCF]\d{3}\s', line):
            useful_lines.append(line)
            continue
        # pytest FAILED summary lines
        if line.startswith("FAILED") or "AssertionError" in line:
            useful_lines.append(line)
            capture = True
            continue
        # short tracebacks around failures
        if capture:
            useful_lines.append(line)
            if line.strip() == "" or line.startswith("="):
                capture = False

    return "\n".join(useful_lines) if useful_lines else log[:3000]


def build_prompt(errors: str, source_code: str, source_path: str) -> str:
    return f"""You are a senior Python developer doing a code review and bug fix.

CI/CD pipeline failed. Here are the errors:

```
{errors}
```

Here is the current source file ({source_path}):

```python
{source_code}
```

Respond ONLY with a valid JSON object in this exact format (no markdown, no explanation outside the JSON):

{{
  "issue_summary": "one-sentence summary of what is broken",
  "root_cause": "concise technical explanation of the root cause",
  "fix_description": "what changes are needed and why",
  "fixed_code": "the complete corrected Python file as a string"
}}

Rules for fixed_code:
- Return the ENTIRE file, not just the changed lines
- Fix all bugs and linting issues present
- Do NOT add any markdown fences inside the JSON string
- Escape newlines as \\n inside the JSON string value
"""


def call_gemini(prompt: str) -> dict:
    """Send the prompt to Gemini and parse the JSON response."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("[INFO] Sending failure logs to Gemini for analysis...")
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip accidental markdown fences if Gemini adds them
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Gemini returned non-JSON response: {e}")
        print("[DEBUG] Raw response snippet:", raw[:500])
        sys.exit(1)

    return result


def save_output(data: dict, output_path: str):
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[INFO] Gemini analysis saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze CI failures with Gemini")
    parser.add_argument("--log", required=True, help="Path to CI failure log file")
    parser.add_argument("--source", required=True, help="Path to the failing source file")
    parser.add_argument("--output", required=True, help="Path to write Gemini fix JSON")
    args = parser.parse_args()

    print(f"[INFO] Loading log: {args.log}")
    log = load_log(args.log)

    print(f"[INFO] Loading source: {args.source}")
    source = load_source(args.source)

    errors = extract_relevant_errors(log)
    print(f"[INFO] Extracted {len(errors.splitlines())} relevant error lines")

    prompt = build_prompt(errors, source, args.source)
    fix_data = call_gemini(prompt)

    # Attach metadata for downstream scripts
    fix_data["source_path"] = args.source

    print("\n[RESULT] Issue Summary:", fix_data.get("issue_summary"))
    print("[RESULT] Root Cause:", fix_data.get("root_cause"))
    print("[RESULT] Fix Description:", fix_data.get("fix_description"))

    save_output(fix_data, args.output)


if __name__ == "__main__":
    main()
