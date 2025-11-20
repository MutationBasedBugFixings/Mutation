#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Tables 9, 10, and 11.
Combines:
1. Mutation Logs (logs/) for Table 10 & 11.
2. Repair Results (results/*_apr_summary.csv) for Table 9.

UPDATES:
- Saves all tables to CSV files in the 'results/' directory.
"""

import os
import csv
import sys
import re
from pathlib import Path
from collections import defaultdict
from typing import Tuple, Dict, List

# ============================================================
# CONFIGURATION
# ============================================================
EXPROOT = os.environ.get("EXPERIMENT_ROOT", "/home1/furqan/my_mutation_experiments")
LOGS_ROOT = Path(EXPROOT) / "logs"
RESULTS_ROOT = Path(EXPROOT) / "results"

OPERATOR_MAP = {
    "ROR": "ROR", "COR": "COR", "LVR": "LVR", "STD": "STD",
    "AOR": "AOR", "SOR": "SOR", "LOR": "LOR", "ORU": "Other", "EVR": "Other"
}
KNOWN_OPS = ["ROR", "COR", "LVR", "STD", "AOR", "SOR", "LOR", "Other"]

# ============================================================
# DATA COLLECTION
# ============================================================

class ProjectStats:
    def __init__(self, name):
        self.name = name
        self.bugs_analyzed = set()
        
        # Mutation Stats (From Logs)
        self.total_mutants = 0
        self.killed_mutants = 0
        self.survived_mutants = 0
        self.live_ops = defaultdict(int)
        
        # APR Stats (From Results CSV)
        self.apr_generated = 0
        self.apr_plausible = 0
        self.apr_correct = 0
        self.fixed_bug_ids = set()

def normalize_operator(raw_op):
    base = raw_op.split("<")[0]
    if base in OPERATOR_MAP:
        return OPERATOR_MAP[base]
    return "Other"

def parse_major_details(log_dir: Path) -> Tuple[int, int, int, dict]:
    """Reads mutants.log and kill.csv."""
    mutants_log = log_dir / "mutants.log"
    kill_csv = log_dir / "kill.csv"

    if not mutants_log.exists():
        return 0, 0, 0, {}

    # 1. Read Kill Status
    killed_ids = set()
    if kill_csv.exists():
        with kill_csv.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row: continue
                mid = row[0]
                outcome = row[-1].upper()
                if outcome in ["KILLED", "TIMEOUT", "MEMORY_ERROR", "RUNTIME_ERROR", "EXC"]:
                    killed_ids.add(mid)

    # 2. Read Definitions
    total = 0
    killed = 0
    survived = 0
    live_ops = defaultdict(int)

    with mutants_log.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split(":")
            if len(parts) < 2: continue
            mid = parts[0]
            raw_op = parts[1]
            
            total += 1
            if mid in killed_ids:
                killed += 1
            else:
                survived += 1
                op_group = normalize_operator(raw_op)
                live_ops[op_group] += 1

    return total, killed, survived, live_ops

def load_apr_results(projects: Dict[str, ProjectStats]):
    """Reads results/{Project}_apr_summary.csv to fill Table 9 left side."""
    if not RESULTS_ROOT.exists():
        return

    for csv_file in RESULTS_ROOT.glob("*_apr_summary.csv"):
        proj_name = csv_file.name.split("_")[0]
        
        if proj_name not in projects:
            projects[proj_name] = ProjectStats(proj_name)
        
        stats = projects[proj_name]
        
        with csv_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    gen = int(row.get("Gen_Patches", 0))
                    plaus = int(row.get("Plausible_Patches", 0))
                    corr = int(row.get("Correct_Patches", 0))
                    bug_id = row.get("Bug")

                    stats.apr_generated += gen
                    stats.apr_plausible += plaus
                    stats.apr_correct   += corr
                    
                    if plaus > 0 and bug_id:
                        stats.fixed_bug_ids.add(bug_id)
                except ValueError:
                    continue

def collect_data():
    projects = {} 

    if not LOGS_ROOT.exists():
        print(f"[ERROR] Logs directory not found at {LOGS_ROOT}")
        sys.exit(1)
    
    target_proj = sys.argv[1] if len(sys.argv) > 1 else None

    # 1. Parse Mutation Logs
    sorted_dirs = sorted(LOGS_ROOT.iterdir(), key=lambda x: x.name)
    if target_proj:
        print(f"Filtering for project: {target_proj}")

    for d in sorted_dirs:
        if not d.is_dir(): continue
        match = re.match(r"^([A-Za-z]+)-(\d+)$", d.name)
        if not match: continue
        
        proj_name = match.group(1)
        bug_id = match.group(2)

        if target_proj and proj_name != target_proj: continue

        if proj_name not in projects:
            projects[proj_name] = ProjectStats(proj_name)
        
        stats = projects[proj_name]
        t, k, s, ops = parse_major_details(d)
        
        if t > 0:
            stats.bugs_analyzed.add(bug_id)
            stats.total_mutants += t
            stats.killed_mutants += k
            stats.survived_mutants += s
            for op, count in ops.items():
                stats.live_ops[op] += count

    # 2. Parse APR Results
    load_apr_results(projects)

    return projects

# ============================================================
# SAVING TABLES
# ============================================================

def save_table_9(projects):
    outfile = RESULTS_ROOT / "table9_execution_results.csv"
    print(f"Saving Table 9 to {outfile}...")
    
    # Print to Console
    print("\n" + "="*110)
    print("Table 9. Dynamic execution results (APR & Mutation Statistics)")
    print("="*110)
    header_fmt = "{:<15} {:<6} {:<10} {:<10} {:<10} {:<10} | {:<10} {:<10} {:<8}"
    print(header_fmt.format("Project", "Bugs", "Gen.Patch", "Plaus.P", "Corr.P", "Fixed", "Mutants", "Killed", "KillRate"))
    print("-" * 110)

    # Write to CSV
    with outfile.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Project", "Bugs", "Gen_Patches", "Plausible_Patches", "Correct_Patches", "Fixed_Bugs", "Mutants", "Killed", "Kill_Rate"])

        for name in sorted(projects.keys()):
            p = projects[name]
            if p.total_mutants == 0 and p.apr_generated == 0: continue
            
            rate = p.killed_mutants / p.total_mutants if p.total_mutants > 0 else 0.0
            fixed_count = len(p.fixed_bug_ids)
            
            # Console
            print(header_fmt.format(
                name, len(p.bugs_analyzed),
                p.apr_generated, p.apr_plausible, p.apr_correct, fixed_count,
                p.total_mutants, p.killed_mutants, f"{rate:.2f}"
            ))
            
            # CSV
            writer.writerow([
                name, len(p.bugs_analyzed),
                p.apr_generated, p.apr_plausible, p.apr_correct, fixed_count,
                p.total_mutants, p.killed_mutants, f"{rate:.2f}"
            ])
    print("-" * 110)


def save_table_10(projects):
    outfile = RESULTS_ROOT / "table10_summary.csv"
    print(f"Saving Table 10 to {outfile}...")

    print("\n" + "="*80)
    print("Table 10. Dynamic execution summary")
    print("="*80)
    header_fmt = "{:<15} {:<10} {:<15} {:<15} {:<15}"
    print(header_fmt.format("Project", "NumBugs", "Total Mutants", "Plausible(LIVE)", "Incorrect(KILLED)"))
    print("-" * 80)

    with outfile.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Project", "NumBugs", "Total_Mutants", "Plausible_Live", "Incorrect_Killed"])

        for name in sorted(projects.keys()):
            p = projects[name]
            if p.total_mutants == 0: continue
            
            # Console
            print(header_fmt.format(
                name, len(p.bugs_analyzed), p.total_mutants, p.survived_mutants, p.killed_mutants
            ))
            
            # CSV
            writer.writerow([
                name, len(p.bugs_analyzed), p.total_mutants, p.survived_mutants, p.killed_mutants
            ])
    print("-" * 80)


def save_table_11(projects):
    outfile = RESULTS_ROOT / "table11_operators.csv"
    print(f"Saving Table 11 to {outfile}...")

    print("\n" + "="*90)
    print("Table 11. Plausible (LIVE) mutant counts per operator")
    print("="*90)
    
    # Headers
    ops_header_str = "".join([f"{op:<8}" for op in KNOWN_OPS])
    print(f"{'Project':<15} {ops_header_str}")
    print("-" * 90)

    with outfile.open("w", newline="") as f:
        writer = csv.writer(f)
        # CSV Header: Project, ROR, COR, ...
        writer.writerow(["Project"] + KNOWN_OPS)

        for name in sorted(projects.keys()):
            p = projects[name]
            if p.total_mutants == 0: continue
            
            # Prepare row data
            row_counts = [p.live_ops.get(op, 0) for op in KNOWN_OPS]
            
            # Console
            counts_str = "".join([f"{val:<8}" for val in row_counts])
            print(f"{name:<15} {counts_str}")
            
            # CSV
            writer.writerow([name] + row_counts)
    print("-" * 90)

def main():
    data = collect_data()
    if not data:
        print("No data found.")
        return
    
    # Ensure results dir exists
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)

    save_table_9(data)
    save_table_10(data)
    save_table_11(data)

if __name__ == "__main__":
    main()
