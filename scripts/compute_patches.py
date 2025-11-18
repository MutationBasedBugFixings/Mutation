#!/usr/bin/env python3
import os
import csv
import argparse
from collections import Counter, defaultdict


def read_kill_file(kill_path):
    status_by_id = {}
    with open(kill_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) < 2:
                continue
            try:
                mid = int(row[0])
            except Exception:
                continue
            status_by_id[mid] = row[1].strip().upper()
    return status_by_id


def read_mutants_log(mutants_path):
    op_by_id = {}
    if not os.path.exists(mutants_path):
        return op_by_id

    with open(mutants_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue
            parts = line.split(":", 2)
            try:
                mid = int(parts[0])
            except Exception:
                continue
            op = parts[1].strip()
            op_by_id[mid] = op
    return op_by_id


def discover_bug_dirs(logs_root):
    bug_dirs = []
    for name in os.listdir(logs_root):
        full = os.path.join(logs_root, name)
        if os.path.isdir(full) and "-" in name:
            project = name.split("-", 1)[0]
            bug_dirs.append((project, name, full))
    bug_dirs.sort(key=lambda x: (x[0], x[1]))
    return bug_dirs


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(row)


def run_for_logs_root(logs_root, project_filter=None):
    """
    Process a single logs root (e.g., logs_lang/) and write CSVs to results/<Project>/.
    """
    if not os.path.isdir(logs_root):
        print(f"[WARN] Logs root not found: {logs_root}")
        return

    bug_dirs = discover_bug_dirs(logs_root)
    if project_filter:
        bug_dirs = [bd for bd in bug_dirs if bd[0] == project_filter]

    if not bug_dirs:
        print(f"[WARN] No matching bug dirs in {logs_root} (project_filter={project_filter})")
        return

    per_bug_rows = []
    per_project = defaultdict(lambda: {
        "bugs": 0,
        "total": 0,
        "plausible": 0,
        "incorrect": 0,
    })
    per_operator = defaultdict(Counter)

    # ---- Process each bug folder ----
    for project, bug_name, bug_dir in bug_dirs:
        kill_path = os.path.join(bug_dir, "kill.csv")
        mutants_path = os.path.join(bug_dir, "mutants.log")

        if not os.path.exists(kill_path):
            continue

        status = read_kill_file(kill_path)
        total = len(status)
        plausible_ids = [m for m, s in status.items() if s == "LIVE"]
        incorrect = total - len(plausible_ids)

        ops = read_mutants_log(mutants_path)
        for mid in plausible_ids:
            op = ops.get(mid, "UNKNOWN")
            per_operator[project][op] += 1

        per_bug_rows.append([project, bug_name, total, len(plausible_ids), incorrect])

        per_project[project]["bugs"] += 1
        per_project[project]["total"] += total
        per_project[project]["plausible"] += len(plausible_ids)
        per_project[project]["incorrect"] += incorrect

    # ---- Prepare CSV files ----
    for project in sorted(per_project.keys()):
        out_dir = os.path.join("results", project)
        os.makedirs(out_dir, exist_ok=True)

        # 1. per bug
        bug_csv = os.path.join(out_dir, "per_bug_summary.csv")
        write_csv(
            bug_csv,
            ["Project", "Bug", "TotalMutants", "Plausible(LIVE)", "Incorrect"],
            [row for row in per_bug_rows if row[0] == project],
        )

        # 2. per project
        proj_csv = os.path.join(out_dir, "per_project_summary.csv")
        pr = per_project[project]
        write_csv(
            proj_csv,
            ["Project", "NumBugs", "TotalMutants", "Plausible(LIVE)", "Incorrect"],
            [[project, pr["bugs"], pr["total"], pr["plausible"], pr["incorrect"]]],
        )

        # 3. operator usage
        op_csv = os.path.join(out_dir, "operator_usage.csv")
        op_rows = [[project, op, cnt] for op, cnt in sorted(per_operator[project].items())]
        write_csv(op_csv, ["Project", "Operator", "PlausibleCount"], op_rows)

        print(f"✔ CSV files written to: {out_dir}/")


def discover_all_logs_roots(base_dir="."):
    """
    Find all directories named 'logs_*' under base_dir (e.g., logs_lang, logs_math, ...).
    """
    roots = []
    for name in os.listdir(base_dir):
        full = os.path.join(base_dir, name)
        if os.path.isdir(full) and name.startswith("logs_"):
            roots.append(full)
    roots.sort()
    return roots


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs-root", default="", help="Path to a single logs root (e.g., logs_lang).")
    parser.add_argument("--project", default="", help="Filter by project name inside logs root (e.g., Lang).")
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="If set, automatically process all logs_* directories under the current folder."
    )
    args = parser.parse_args()

    if args.all_projects:
        # Example usage: python3 compute_patches.py --all-projects
        for root in discover_all_logs_roots("."):
            print(f"\n=== Processing logs root: {root} ===")
            run_for_logs_root(root, project_filter=None)
    else:
        # Single logs root (old behaviour)
        logs_root = args.logs_root or "logs"
        run_for_logs_root(logs_root, args.project or None)
