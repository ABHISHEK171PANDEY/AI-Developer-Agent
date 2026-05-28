#!/usr/bin/env python3
"""
apply_fix.py
Reads Gemini's fix JSON and overwrites the affected source file.
"""

import argparse
import json
import os
import sys


def load_fix(fix_path: str) -> dict:
    if not os.path.exists(fix_path):
        print(f"[ERROR] Fix file not found: {fix_path}")
        sys.exit(1)
    with open(fix_path) as f:
        return json.load(f)


def validate_python(code: str) -> bool:
    """Compile-check the generated code before writing it."""
    try:
        compile(code, "<gemini_fix>", "exec")
        return True
    except SyntaxError as e:
        print(f"[ERROR] Gemini-generated code has a syntax error: {e}")
        return False


def apply_fix(fix_data: dict, override_source: str | None = None):
    source_path = override_source or fix_data.get("source_path")
    if not source_path:
        print("[ERROR] No source_path in fix data and --source not provided.")
        sys.exit(1)

    fixed_code = fix_data.get("fixed_code", "")
    if not fixed_code:
        print("[ERROR] Gemini fix contains no fixed_code.")
        sys.exit(1)

    # Normalise escaped newlines that sometimes survive JSON serialisation
    fixed_code = fixed_code.replace("\\n", "\n")

    if not validate_python(fixed_code):
        sys.exit(1)

    # Back up the original
    backup_path = source_path + ".bak"
    if os.path.exists(source_path):
        with open(source_path) as f:
            original = f.read()
        with open(backup_path, "w") as f:
            f.write(original)
        print(f"[INFO] Original backed up to {backup_path}")

    with open(source_path, "w") as f:
        f.write(fixed_code)

    print(f"[INFO] Fix applied to {source_path}")
    print(f"[INFO] Summary : {fix_data.get('issue_summary')}")
    print(f"[INFO] Fix desc: {fix_data.get('fix_description')}")


def main():
    parser = argparse.ArgumentParser(description="Apply Gemini-generated fix to source file")
    parser.add_argument("--fix", required=True, help="Path to Gemini fix JSON")
    parser.add_argument("--source", help="Override source path (optional)")
    args = parser.parse_args()

    fix_data = load_fix(args.fix)
    apply_fix(fix_data, override_source=args.source)


if __name__ == "__main__":
    main()
