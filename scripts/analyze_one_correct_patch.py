#!/usr/bin/env python3
"""
Analyze patch type/granularity for ONLY ONE correct LLM patch per bug.

Correct patch definition:
  status == "correct"

Backup definition:
  patch_apply_ok == True
  compile_ok == True
  trigger_tests_pass == True
  all_tests_pass == True

Main purpose:
  If one bug has multiple correct LLM patches, this script keeps only ONE patch.

Default selection:
  first correct patch by lowest run_id

Alternative:
  --select smallest
  chooses the smallest correct patch by:
    files_touched, hunks, changed_line_estimate, added_lines+deleted_lines, run_id

Run from scripts folder:
  python analyze_one_correct_patch_per_bug_types.py \
    --eval-csv results_eval/llm_patch_evaluation_results.csv \
    --project-root .. \
    --select first

Outputs:
  results_eval/one_correct_patch_per_bug_type_analysis.csv
  results_eval/one_correct_patch_per_bug_type_summary.csv
"""

import argparse
import csv
import re
from pathlib import Path
from collections import Counter, defaultdict


HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)

IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
STRING_RE = re.compile(r"""(['"]).*?\1""")

OPERATORS = [
    "==", "!=", "<=", ">=", "&&", "||", "<<", ">>",
    "+=", "-=", "*=", "/=", "%=",
    "+", "-", "*", "/", "%", "<", ">", "=", "!", "&", "|", "^"
]


def safe_int(value, default=10**9):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def to_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def is_correct_patch(row):
    status_correct = row.get("status", "").strip().lower() == "correct"

    flags_correct = (
        to_bool(row.get("patch_apply_ok", "False"))
        and to_bool(row.get("compile_ok", "False"))
        and to_bool(row.get("trigger_tests_pass", "False"))
        and to_bool(row.get("all_tests_pass", "False"))
    )

    return status_correct or flags_correct


def normalize_ws(s):
    return re.sub(r"\s+", "", s.strip())


def tokenize_ops(s):
    found = []
    for op in sorted(OPERATORS, key=len, reverse=True):
        if op in s:
            found.append(op)
    return found


def method_calls(s):
    return re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", s)


def identifiers(s):
    return IDENT_RE.findall(s)


def literals(s):
    nums = NUMBER_RE.findall(s)
    strs = STRING_RE.findall(s)
    bools = re.findall(r"\b(true|false|null|None|True|False)\b", s)
    return nums + strs + bools


def is_condition_line(s):
    s = s.strip()
    return (
        s.startswith("if ")
        or s.startswith("if(")
        or s.startswith("else if")
        or s.startswith("while ")
        or s.startswith("while(")
        or s.startswith("for ")
        or s.startswith("for(")
        or s.startswith("assert ")
        or s.startswith("assert(")
        or ("?" in s and ":" in s)
    )


def is_return_line(s):
    return s.strip().startswith("return")


def is_import_line(s):
    s = s.strip()
    return s.startswith("import ") or s.startswith("from ")


def is_exception_line(s):
    s = s.strip()
    return (
        s.startswith("throw ")
        or s.startswith("raise ")
        or "Exception" in s
        or "Error" in s
    )


def classify_replacement(old, new):
    old_s = old.strip()
    new_s = new.strip()

    if normalize_ws(old_s) == normalize_ws(new_s):
        return "formatting/whitespace change"

    if is_import_line(old_s) or is_import_line(new_s):
        return "import change"

    if is_exception_line(old_s) or is_exception_line(new_s):
        return "exception/error-handling change"

    if is_return_line(old_s) or is_return_line(new_s):
        if literals(old_s) != literals(new_s):
            return "return literal change"
        if tokenize_ops(old_s) != tokenize_ops(new_s):
            return "return operator change"
        return "return expression change"

    if is_condition_line(old_s) or is_condition_line(new_s):
        if tokenize_ops(old_s) != tokenize_ops(new_s):
            return "condition/operator change"
        if literals(old_s) != literals(new_s):
            return "condition/literal change"
        if identifiers(old_s) != identifiers(new_s):
            return "condition/identifier change"
        return "condition expression change"

    old_calls = method_calls(old_s)
    new_calls = method_calls(new_s)

    if old_calls or new_calls:
        if old_calls != new_calls:
            return "method/function call change"
        if old_calls == new_calls and normalize_ws(old_s) != normalize_ws(new_s):
            return "method/function argument change"

    if literals(old_s) != literals(new_s):
        return "literal/constant change"

    if tokenize_ops(old_s) != tokenize_ops(new_s):
        return "operator change"

    if identifiers(old_s) != identifiers(new_s):
        return "identifier/variable change"

    if "=" in old_s or "=" in new_s:
        return "assignment/update change"

    return "single-line replacement"


def classify_patch_type(added_lines, deleted_lines):
    added = [x for x in added_lines if x.strip()]
    deleted = [x for x in deleted_lines if x.strip()]

    if not added and not deleted:
        return "empty/unknown"

    if added and not deleted:
        if any(is_condition_line(x) for x in added):
            return "insert condition/guard"
        if any(is_return_line(x) for x in added):
            return "insert return"
        if any(is_exception_line(x) for x in added):
            return "insert exception/error handling"
        if any(is_import_line(x) for x in added):
            return "insert import"
        return "insert-only"

    if deleted and not added:
        if any(is_condition_line(x) for x in deleted):
            return "delete condition/guard"
        if any(is_return_line(x) for x in deleted):
            return "delete return"
        if any(is_exception_line(x) for x in deleted):
            return "delete exception/error handling"
        if any(is_import_line(x) for x in deleted):
            return "delete import"
        return "delete-only"

    if len(added) == 1 and len(deleted) == 1:
        return classify_replacement(deleted[0], added[0])

    if any(is_condition_line(x) for x in added + deleted):
        return "multi-line condition change"

    if any(is_return_line(x) for x in added + deleted):
        return "multi-line return change"

    if any(is_exception_line(x) for x in added + deleted):
        return "multi-line exception/error-handling change"

    if len(added) == len(deleted):
        return "multi-line replacement"

    return "mixed insert/delete"


def parse_unified_diff(text):
    files = []
    current_file = None
    current_hunk = None

    for raw in text.splitlines():
        line = raw.rstrip("\n")

        if line.startswith("diff --git "):
            if current_file is not None:
                files.append(current_file)
            current_file = {"old_file": None, "new_file": None, "hunks": []}
            current_hunk = None

        elif line.startswith("--- "):
            if current_file is None:
                current_file = {"old_file": None, "new_file": None, "hunks": []}
            current_file["old_file"] = line[4:].strip()

        elif line.startswith("+++ "):
            if current_file is None:
                current_file = {"old_file": None, "new_file": None, "hunks": []}
            current_file["new_file"] = line[4:].strip()

        elif line.startswith("@@ "):
            if current_file is None:
                current_file = {"old_file": None, "new_file": None, "hunks": []}

            current_hunk = {"header": line, "added": [], "deleted": []}
            current_file["hunks"].append(current_hunk)

        elif current_hunk is not None:
            if line.startswith("\\ No newline"):
                continue
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk["added"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk["deleted"].append(line[1:])

    if current_file is not None:
        files.append(current_file)

    return files


def resolve_patch_path(raw_path, project_root):
    p = Path(raw_path)

    if p.exists():
        return p

    # If CSV has absolute paths from another run, try resolving by filename.
    filename = p.name

    candidates = [
        project_root / "scripts" / "patches_deepseek" / filename,
        project_root / "scripts" / "results_eval" / filename,
        project_root / "patches_deepseek" / filename,
        project_root / "results_eval" / filename,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Last fallback: recursive filename search under scripts.
    scripts_dir = project_root / "scripts"
    if scripts_dir.exists():
        matches = list(scripts_dir.rglob(filename))
        if matches:
            return matches[0]

    return None


def analyze_patch_file(patch_path, meta):
    text = patch_path.read_text(encoding="utf-8", errors="ignore")
    files = parse_unified_diff(text)

    source_files = []
    total_hunks = 0
    total_added = 0
    total_deleted = 0
    all_added = []
    all_deleted = []

    for f in files:
        filename = f["new_file"] or f["old_file"] or "unknown"

        if filename == "/dev/null":
            filename = f["old_file"] or "unknown"

        source_files.append(filename)
        total_hunks += len(f["hunks"])

        for h in f["hunks"]:
            total_added += len(h["added"])
            total_deleted += len(h["deleted"])
            all_added.extend(h["added"])
            all_deleted.extend(h["deleted"])

    files_touched = len(set(source_files))
    changed_line_estimate = max(total_added, total_deleted)

    if files_touched == 1 and total_hunks == 1 and changed_line_estimate <= 1:
        granularity = "single-line"
    elif files_touched == 1 and total_hunks == 1 and changed_line_estimate > 1:
        granularity = "multi-line single-hunk"
    elif files_touched == 1 and total_hunks > 1:
        granularity = "multi-hunk single-file"
    elif files_touched > 1:
        granularity = "multi-file"
    else:
        granularity = "empty/unknown"

    return {
        **meta,
        "patch_path": str(patch_path),
        "files_touched": files_touched,
        "hunks": total_hunks,
        "added_lines": total_added,
        "deleted_lines": total_deleted,
        "changed_line_estimate": changed_line_estimate,
        "granularity": granularity,
        "patch_type": classify_patch_type(all_added, all_deleted),
        "files": ";".join(sorted(set(source_files))),
    }


def load_correct_rows(eval_csv):
    correct_rows = []

    with eval_csv.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if is_correct_patch(row):
                correct_rows.append(row)

    return correct_rows


def choose_one_per_bug(correct_rows, project_root, select_mode):
    grouped = defaultdict(list)

    for row in correct_rows:
        key = (row.get("project", "").strip(), str(row.get("bug_id", "")).strip())
        grouped[key].append(row)

    selected_rows = []
    skipped_missing_patch = []

    for key, rows in grouped.items():
        rows = sorted(rows, key=lambda r: safe_int(r.get("run_id", "")))

        if select_mode == "first":
            selected_rows.append(rows[0])
            continue

        if select_mode == "smallest":
            analyzed_candidates = []

            for row in rows:
                raw_patch = row.get("patch_file", "").strip()
                patch_path = resolve_patch_path(raw_patch, project_root)

                if patch_path is None:
                    skipped_missing_patch.append(raw_patch)
                    continue

                meta = {
                    "project": row.get("project", ""),
                    "bug_id": row.get("bug_id", ""),
                    "run_id": row.get("run_id", ""),
                    "status": row.get("status", ""),
                    "correct_patch_candidates_for_bug": len(rows),
                    "selected_policy": select_mode,
                }

                analyzed = analyze_patch_file(patch_path, meta)
                analyzed["_raw_row"] = row

                analyzed_candidates.append(analyzed)

            if not analyzed_candidates:
                continue

            analyzed_candidates = sorted(
                analyzed_candidates,
                key=lambda r: (
                    safe_int(r["files_touched"]),
                    safe_int(r["hunks"]),
                    safe_int(r["changed_line_estimate"]),
                    safe_int(r["added_lines"]) + safe_int(r["deleted_lines"]),
                    safe_int(r["run_id"]),
                )
            )

            selected_rows.append(analyzed_candidates[0]["_raw_row"])
            continue

        raise ValueError(f"Unknown select mode: {select_mode}")

    return selected_rows, grouped, skipped_missing_patch


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--eval-csv",
        default="results_eval/llm_patch_evaluation_results.csv",
        help="CSV produced by patch evaluation."
    )

    parser.add_argument(
        "--project-root",
        default="..",
        help="Project root. If running from scripts folder, use .."
    )

    parser.add_argument(
        "--select",
        choices=["first", "smallest"],
        default="first",
        help="How to select one correct patch per bug. Default: first"
    )

    parser.add_argument(
        "--out",
        default="results_eval/one_correct_patch_per_bug_type_analysis.csv",
        help="Detailed output CSV."
    )

    parser.add_argument(
        "--summary-out",
        default="results_eval/one_correct_patch_per_bug_type_summary.csv",
        help="Summary output CSV."
    )

    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    eval_csv = Path(args.eval_csv)
    out_csv = Path(args.out)
    summary_csv = Path(args.summary_out)

    if not eval_csv.exists():
        raise SystemExit(f"Evaluation CSV not found: {eval_csv}")

    correct_rows = load_correct_rows(eval_csv)

    selected_rows, grouped, skipped_missing_patch = choose_one_per_bug(
        correct_rows=correct_rows,
        project_root=project_root,
        select_mode=args.select,
    )

    final_rows = []
    missing_patch_files = []

    for row in selected_rows:
        raw_patch = row.get("patch_file", "").strip()
        patch_path = resolve_patch_path(raw_patch, project_root)

        if patch_path is None:
            missing_patch_files.append(raw_patch)
            continue

        key = (row.get("project", "").strip(), str(row.get("bug_id", "")).strip())

        meta = {
            "project": row.get("project", ""),
            "bug_id": row.get("bug_id", ""),
            "run_id": row.get("run_id", ""),
            "status": row.get("status", ""),
            "correct_patch_candidates_for_bug": len(grouped[key]),
            "selected_policy": args.select,
        }

        final_rows.append(analyze_patch_file(patch_path, meta))

    if not final_rows:
        raise SystemExit("No selected correct patch files were found/analyzed.")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "project",
        "bug_id",
        "run_id",
        "status",
        "correct_patch_candidates_for_bug",
        "selected_policy",
        "patch_path",
        "files_touched",
        "hunks",
        "added_lines",
        "deleted_lines",
        "changed_line_estimate",
        "granularity",
        "patch_type",
        "files",
    ]

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)

    granularity_counter = Counter(r["granularity"] for r in final_rows)
    patch_type_counter = Counter(r["patch_type"] for r in final_rows)

    total_bugs_with_correct_patch = len(grouped)
    total_selected_analyzed = len(final_rows)

    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["section", "name", "count", "percentage"])

        writer.writerow(["overall", "total_correct_patches_before_deduplication", len(correct_rows), ""])
        writer.writerow(["overall", "bugs_with_at_least_one_correct_patch", total_bugs_with_correct_patch, ""])
        writer.writerow(["overall", "selected_correct_patches_analyzed", total_selected_analyzed, ""])
        writer.writerow(["overall", "selection_policy", args.select, ""])

        for name, count in granularity_counter.most_common():
            writer.writerow([
                "granularity",
                name,
                count,
                round(count / total_selected_analyzed * 100, 2)
            ])

        for name, count in patch_type_counter.most_common():
            writer.writerow([
                "patch_type",
                name,
                count,
                round(count / total_selected_analyzed * 100, 2)
            ])

    print("Done.")
    print(f"Correct patches before deduplication: {len(correct_rows)}")
    print(f"Bugs with at least one correct patch: {total_bugs_with_correct_patch}")
    print(f"Selected correct patches analyzed: {total_selected_analyzed}")
    print(f"Selection policy: {args.select}")
    print(f"Detailed output: {out_csv}")
    print(f"Summary output:  {summary_csv}")

    if missing_patch_files:
        print("\nWARNING: Some selected patch files were missing:")
        for p in missing_patch_files[:20]:
            print(f"  {p}")
        if len(missing_patch_files) > 20:
            print(f"  ... and {len(missing_patch_files) - 20} more")

    print("\nGranularity summary:")
    for name, count in granularity_counter.most_common():
        print(f"  {name}: {count}")

    print("\nPatch-type summary:")
    for name, count in patch_type_counter.most_common():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
