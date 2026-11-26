#!/usr/bin/env python3
"""
Reconstruct the RQ4 92-bug stratified sample.

IMPORTANT:
- The RQ4 population is the 809 non-Chart Defects4J bugs (835 - 26 Chart).
- Do NOT use RQ5 strict_eligible as an RQ4 inclusion filter.
- Each RQ4 bug must have one reviewed primary RQ4 operator stratum:
  CI, MCR, MRV, LOR, VA, ROR, or Others.
- Multi-operator/composite annotations must be resolved explicitly in
  rq4_operator_assignments.csv. This script will not arbitrarily choose
  the first operator from a multi-operator annotation.
- The script refuses to generate a final sample unless it verifies exactly
  809 unique non-Chart bugs and complete operator assignments.

Expected inputs:
  --population: original 835-row Defects4J population CSV
  --mapping: cleaned_bug_operator_sets.csv (RQ5-derived mapping source)
  --assignments: reviewed RQ4 operator assignments CSV

Required columns:
  population: project, bug_id
  mapping: project, bug_id, raw_operators (optional, for audit only)
  assignments: project, bug_id, rq4_operator

Run from repository root, for example:
python RQ4/scripts/reconstruct_sample.py \
  --population transparency/defects4j.csv \
  --mapping RQ4/data/cleaned_bug_operator_sets.csv \
  --assignments RQ4/data/rq4_operator_assignments.csv \
  --outdir RQ4/sampling \
  --seed 20261126
"""

from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys
import pandas as pd
import numpy as np

QUOTAS = {
    "CI": 15,
    "MCR": 14,
    "MRV": 10,
    "LOR": 10,
    "VA": 8,
    "ROR": 7,
    "Others": 28,
}
EXPECTED_POPULATION = 809
EXPECTED_SAMPLE = 92
CHART_LABELS = {"chart"}
REQUIRED_ASSIGNMENT_COLUMNS = {"project", "bug_id", "rq4_operator"}


def norm_project(value: object) -> str:
    return str(value).strip().lower()


def norm_bug_id(value: object) -> str:
    return str(value).strip()


def read_csv(path: str, label: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def find_col(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    raise ValueError(
        f"{label}: could not find any of columns {candidates}. "
        f"Available columns: {list(df.columns)}"
    )


def add_keys(df: pd.DataFrame, project_col: str, bug_col: str) -> pd.DataFrame:
    out = df.copy()
    out["_project_key"] = out[project_col].map(norm_project)
    out["_bug_key"] = out[bug_col].map(norm_bug_id)
    out["_key"] = out["_project_key"] + "::" + out["_bug_key"]
    return out


def largest_remainder_allocation(counts: pd.Series, quota: int) -> pd.Series:
    """Allocate a stratum quota proportionally across projects."""
    if int(counts.sum()) < quota:
        raise ValueError(
            f"Stratum population {int(counts.sum())} is smaller than quota {quota}."
        )
    exact = counts / counts.sum() * quota
    alloc = np.floor(exact).astype(int)
    remaining = quota - int(alloc.sum())
    remainder_order = (exact - alloc).sort_values(
        ascending=False, kind="stable"
    ).index
    for project in remainder_order[:remaining]:
        alloc.loc[project] += 1
    return alloc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--population", required=True)
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--assignments", required=True)
    ap.add_argument("--outdir", default="RQ4/sampling")
    ap.add_argument("--seed", type=int, default=20261126)
    args = ap.parse_args()

    population = read_csv(args.population, "Original Defects4J population")
    mapping = read_csv(args.mapping, "Operator mapping")
    assignments = read_csv(args.assignments, "Reviewed RQ4 assignments")

    pop_project = find_col(population, ["project", "project_id"], "Population")
    pop_bug = find_col(population, ["bug_id", "bug", "bugid", "id"], "Population")
    map_project = find_col(mapping, ["project"], "Mapping")
    map_bug = find_col(mapping, ["bug_id", "bug", "bugid"], "Mapping")

    missing_assignment_cols = REQUIRED_ASSIGNMENT_COLUMNS - set(assignments.columns)
    if missing_assignment_cols:
        raise ValueError(
            f"Assignments file missing columns: {sorted(missing_assignment_cols)}"
        )

    population = add_keys(population, pop_project, pop_bug)
    mapping = add_keys(mapping, map_project, map_bug)
    assignments = add_keys(assignments, "project", "bug_id")

    # Validate original population and exclude Chart only.
    population = population[
        ~population["_project_key"].isin(CHART_LABELS)
    ].copy()
    dup_pop = population[population["_key"].duplicated(keep=False)]
    if not dup_pop.empty:
        raise ValueError(
            "Duplicate project/bug IDs in the non-Chart population. "
            "Resolve duplicates before sampling:\n"
            + dup_pop[[pop_project, pop_bug]].to_string(index=False)
        )

    if len(population) != EXPECTED_POPULATION:
        raise ValueError(
            f"Expected exactly {EXPECTED_POPULATION} non-Chart bugs "
            f"(835 original - 26 Chart), but found {len(population)}. "
            "Do not generate a final sample until the population is reconciled."
        )

    # Ensure mapping is joined by project + bug ID, not row order.
    if mapping["_key"].duplicated().any():
        raise ValueError("Mapping contains duplicate project/bug keys.")

    pop_keys = set(population["_key"])
    mapping_keys = set(mapping["_key"])
    missing_mapping = sorted(pop_keys - mapping_keys)
    extra_mapping = sorted(mapping_keys - pop_keys)

    # Assignment file is the authoritative, reviewed RQ4 semantic stratum.
    if assignments["_key"].duplicated().any():
        raise ValueError("Assignments contain duplicate project/bug keys.")
    assignment_keys = set(assignments["_key"])
    missing_assignments = sorted(pop_keys - assignment_keys)
    extra_assignments = sorted(assignment_keys - pop_keys)

    allowed = set(QUOTAS)
    assignments["rq4_operator"] = assignments["rq4_operator"].str.strip()
    invalid = sorted(set(assignments["rq4_operator"]) - allowed)
    if invalid:
        raise ValueError(f"Invalid rq4_operator labels: {invalid}")

    if missing_assignments or extra_assignments:
        raise ValueError(
            "RQ4 operator assignments must cover exactly the 809-bug "
            f"population. Missing={len(missing_assignments)}, "
            f"extra={len(extra_assignments)}. "
            "Complete assignments before sampling."
        )

    # Preserve mapping-coverage audit, but don't silently drop bugs without a mapping.
    if missing_mapping:
        print(
            f"WARNING: {len(missing_mapping)} population bugs have no row in "
            "the RQ5-derived mapping file. Their RQ4 operator assignments "
            "must be supported by the original annotations.",
            file=sys.stderr,
        )

    frame = population.merge(
        assignments[["_key", "rq4_operator"]],
        on="_key",
        how="left",
        validate="one_to_one",
    )
    frame["project"] = frame[pop_project].str.strip()
    frame["bug_id"] = frame[pop_bug].str.strip()

    # Deterministic RNG; project allocation is proportional within each operator stratum.
    rng = np.random.default_rng(args.seed)
    selected = []
    allocation_records = []
    for operator, quota in QUOTAS.items():
        stratum = frame[frame["rq4_operator"].eq(operator)].copy()
        counts = stratum.groupby("project").size().sort_index()
        allocation = largest_remainder_allocation(counts, quota)

        for project, n in allocation.items():
            if n == 0:
                continue
            project_pool = stratum[stratum["project"].eq(project)].copy()
            chosen_positions = rng.choice(
                len(project_pool), size=int(n), replace=False
            )
            chosen = project_pool.iloc[chosen_positions].copy()
            selected.append(chosen)
            allocation_records.append({
                "rq4_operator": operator,
                "project": project,
                "population_in_stratum_project": int(len(project_pool)),
                "sample_quota": int(n),
            })

    sample = pd.concat(selected, ignore_index=True)
    sample = sample.sort_values(
        ["project", "rq4_operator", "bug_id"], kind="stable"
    ).reset_index(drop=True)
    sample.insert(0, "sample_order", range(1, len(sample) + 1))
    sample["sampling_seed"] = args.seed
    sample["population_size"] = EXPECTED_POPULATION
    sample["sampling_method"] = (
        "Proportional project allocation within fixed RQ4 operator strata; "
        "random sampling without replacement"
    )

    if len(sample) != EXPECTED_SAMPLE or sample["_key"].nunique() != EXPECTED_SAMPLE:
        raise RuntimeError("Sample size/uniqueness check failed.")

    sample_counts = sample["rq4_operator"].value_counts().to_dict()
    if sample_counts != QUOTAS:
        raise RuntimeError(
            f"Operator quotas do not match manuscript targets: {sample_counts}"
        )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Export clean, readable sample; no internal keys.
    sample_cols = [
        "sample_order", "project", "bug_id", "rq4_operator",
        "sampling_seed", "population_size", "sampling_method"
    ]
    sample[sample_cols].to_csv(outdir / "sample_92.csv", index=False)

    pd.DataFrame(allocation_records).to_csv(
        outdir / "project_operator_allocation.csv", index=False
    )

    pd.DataFrame([
        {"operator": op, "population_count": int((frame["rq4_operator"] == op).sum()),
         "sample_count": int(sample_counts.get(op, 0)), "target_quota": quota}
        for op, quota in QUOTAS.items()
    ]).to_csv(outdir / "operator_strata_audit.csv", index=False)

    pd.DataFrame([
        {"check": "original_population_after_Chart_exclusion",
         "value": len(population), "expected": EXPECTED_POPULATION},
        {"check": "unique_sampled_bugs", "value": sample["_key"].nunique(),
         "expected": EXPECTED_SAMPLE},
        {"check": "mapping_rows_missing_for_population",
         "value": len(missing_mapping), "expected": 0},
        {"check": "assignment_rows_missing_for_population",
         "value": len(missing_assignments), "expected": 0},
        {"check": "assignment_rows_outside_population",
         "value": len(extra_assignments), "expected": 0},
    ]).to_csv(outdir / "population_reconciliation.csv", index=False)

    # Provenance file records exact input hashes.
    def sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    provenance = pd.DataFrame([
        {"input": "population", "path": args.population, "sha256": sha256(args.population)},
        {"input": "mapping", "path": args.mapping, "sha256": sha256(args.mapping)},
        {"input": "assignments", "path": args.assignments, "sha256": sha256(args.assignments)},
    ])
    provenance.to_csv(outdir / "sampling_provenance.csv", index=False)

    print(f"SUCCESS: generated {len(sample)} unique RQ4 sample bugs.")
    print(f"Sample: {outdir / 'sample_92.csv'}")
    print(f"Seed: {args.seed}")
    print("Operator quotas:", sample_counts)
    print(f"Population mapping rows absent: {len(missing_mapping)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
