# 🤖 AI Dev Agent

> A lightweight GitHub-integrated AI system that monitors pull requests, detects CI/CD failures, analyzes logs with Gemini, and automatically creates a fix PR.

---

## Overview

When a developer opens a PR against `main`, a GitHub Actions pipeline runs linting and tests. If the pipeline **fails**, the AI Dev Agent kicks in:

1. Collects the combined `flake8` + `pytest` logs
2. Reads the failing source file
3. Sends both to **Gemini 2.5 Flash** with a structured debugging prompt
4. Gemini returns a JSON payload: issue summary, root cause, fix description, and corrected code
5. The agent creates a new branch, commits the fix, and opens a PR — automatically

No external services, no databases, no message queues. Just Python, GitHub Actions, and Gemini.

---

## Architecture

```
Developer opens PR
        │
        ▼
┌─────────────────────┐
│  GitHub Actions     │
│  lint-and-test job  │
│  ─────────────────  │
│  flake8  → log      │
│  pytest  → log      │
│  combine → artifact │
└────────┬────────────┘
         │ failure detected
         ▼
┌─────────────────────────────────┐
│  GitHub Actions                 │
│  ai-fix-agent job               │
│  ───────────────────────────── │
│  analyze_failure.py             │
│    └─ extract errors            │
│    └─ call Gemini API  ─────►  Gemini 2.5 Flash
│    └─ save fix JSON    ◄─────  JSON: summary, fix, code
│                                 │
│  apply_fix.py                   │
│    └─ validate Python           │
│    └─ overwrite source file     │
│                                 │
│  create_pr.py                   │
│    └─ git checkout -b ai-fix/…  │
│    └─ git commit + push         │
│    └─ GitHub API → open PR      │
└─────────────────────────────────┘
         │
         ▼
  AI Fix PR opened on GitHub
```

---

## Workflow Diagram

```
[Developer] ──push──► [PR on GitHub]
                              │
                    [Actions: lint-and-test]
                      flake8 ──► log
                      pytest ──► log
                              │
                    ┌─────────▼──────────┐
                    │  Pipeline Failed?  │
                    └─────────┬──────────┘
                         yes  │
                              ▼
                    [Actions: ai-fix-agent]
                              │
                    analyze_failure.py
                      ├── extract errors
                      └── Gemini API call
                              │
                    apply_fix.py
                      └── overwrite source
                              │
                    create_pr.py
                      ├── new branch
                      ├── git commit
                      ├── git push
                      └── GitHub PR API
                              │
                              ▼
                    [AI Fix PR Created] ✅
```

---

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── dev-agent.yml       # GitHub Actions pipeline
├── scripts/
│   ├── analyze_failure.py      # Extract errors + call Gemini
│   ├── apply_fix.py            # Overwrite source with Gemini fix
│   └── create_pr.py            # Branch + commit + GitHub PR
├── src/
│   ├── __init__.py
│   └── calculator.py           # Sample app with intentional bugs
├── tests/
│   ├── __init__.py
│   └── test_calculator.py      # Tests (one intentionally failing)
├── requirements.txt
└── README.md
```

---

## Intentional Issues in the Sample App

`src/calculator.py` contains three deliberate problems to exercise the agent:

| Type | Location | Description |
|------|----------|-------------|
| **Bug** | `divide()` | No zero-division guard → raises `ZeroDivisionError` |
| **Bug** | `calculate_average()` | Divides by `len - 1` instead of `len` → wrong result |
| **Lint** | `calculate_average()` | Unused variable `total` flagged by flake8 (`F841`) |

The test suite includes assertions for correct average calculation and a `ZeroDivisionError` guard, so both bugs cause test failures.

---

## Setup

### 1. Fork / Clone

```bash
git clone https://github.com/YOUR_USERNAME/ai-dev-agent.git
cd ai-dev-agent
```

### 2. Install dependencies locally

```bash
pip install -r requirements.txt
```

### 3. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** in your repo and add:

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key (see below) |
| `AGENT_PAT` | A GitHub Personal Access Token with `repo` scope |

#### Creating `AGENT_PAT`

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token**
3. Select scope: `repo` (full control of private repositories)
4. Copy the token and add it as the `AGENT_PAT` secret

### 4. Configure Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key and add it as the `GEMINI_API_KEY` secret

---

## Local Execution

You can run each step locally to test without GitHub Actions.

### Run linting and tests

```bash
flake8 src/ --max-line-length=100
pytest tests/ -v
```

Expected output: flake8 reports an unused variable; pytest shows one failing test.

### Run the analysis script (requires `GEMINI_API_KEY`)

```bash
# First generate fake logs
flake8 src/ --max-line-length=100 > /tmp/flake8.log 2>&1 || true
pytest tests/ -v --tb=short > /tmp/pytest.log 2>&1 || true
cat /tmp/flake8.log /tmp/pytest.log > /tmp/ci_failure.log

# Run analysis
export GEMINI_API_KEY=your_key_here
python scripts/analyze_failure.py \
  --log /tmp/ci_failure.log \
  --source src/calculator.py \
  --output /tmp/gemini_fix.json
```

### Apply the fix locally

```bash
python scripts/apply_fix.py \
  --fix /tmp/gemini_fix.json \
  --source src/calculator.py
```

### Create the PR (requires `GITHUB_TOKEN` and a clean git state)

```bash
export GITHUB_TOKEN=your_pat_here
python scripts/create_pr.py \
  --fix /tmp/gemini_fix.json \
  --base your-feature-branch \
  --repo YOUR_USERNAME/ai-dev-agent
```

---

## GitHub Actions Execution Flow

1. **Trigger**: A PR is opened or pushed against `main`
2. **`lint-and-test` job** runs flake8 and pytest, saves combined logs as an artifact
3. **`ai-fix-agent` job** runs only if `pipeline_failed == true`:
   - Downloads the log artifact
   - Calls `analyze_failure.py` → Gemini API → saves `gemini_fix.json`
   - Calls `apply_fix.py` → overwrites `src/calculator.py` with the fixed version
   - Calls `create_pr.py` → pushes `ai-fix/<branch>-<timestamp>` and opens a PR
4. A new PR titled `[AI Fix] <issue summary>` appears in the repository

---

## Example: Failed Pipeline

```
FAILED tests/test_calculator.py::test_calculate_average
AssertionError: assert 15.0 == 20.0
 +  where 15.0 = calculate_average([10, 20, 30])

src/calculator.py:16:5: F841 local variable 'total' is assigned to but never used
```

## Example: AI Fix PR Body

```markdown
## 🤖 AI Dev Agent — Automated Fix

### 🔍 Issue Summary
calculate_average divides by len-1 causing wrong results; divide has no zero guard; unused variable total.

### 🧠 Root Cause
Off-by-one error in denominator and missing ZeroDivisionError handling.

### 🔧 Fix Applied
Changed denominator to len(numbers), added zero-division guard in divide(), removed unused variable.
```

---

## License

MIT.
