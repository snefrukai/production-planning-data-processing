# CLAUDE.md

This file provides strict guidance and rules for AI assistants (like Claude/Cursor) when working in the `scripts/` sub-project.

## Single Source of Truth

**DO NOT duplicate architectural documentation or business logic here.**
The `scripts/README.md` file is the absolute single source of truth for both developers and AI.

If you need to understand:

- The project architecture and data pipeline (Excel uploading → Parsing → Backlog Calculation → CSV/XLSX Export)
- Business logic for calculating part dispatch backlog (Pending quantities across production steps)
- Excel data structures, column mapping layouts, and the "Order Theme / PDM / Part Name" resolution rules
- Dataclass models (`models.py`) and utility functions (`utils.py`)

👉 **You MUST use your file reading tools to parse `scripts/README.md` before making architectural decisions.**

## Mandatory AI Verification Rules

Before you claim that any task is "Complete", "Fixed", or "Working", you MUST sequentially run and pass the following checks in the `scripts/` folder:

1. **Test Suite**: Run `pytest test/`. You must visually confirm an `exit 0` with 0 failures.
2. **Static Typing**: Run `mypy .`. You must visually confirm `Success: no issues found`.
3. **Linting & Formatting**: Run `ruff check --fix .` and `ruff format .`.

If you skip these steps, you are violating the core verification rules of this repository. Evidence before claims, always.
