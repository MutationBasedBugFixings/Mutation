#!/usr/bin/env python3
"""Reproduce the supplementary PraPR Coverage@k comparison.

This script does not run PraPR or generate bytecode mutants. It reproduces the
paper's transferred-utility analysis by:
1. reading PraPR's published HD-Repair mutator frequencies;
2. mapping and consolidating concrete PraPR mutators into the paper's unified
   semantic operator families;
3. evaluating the resulting mapped order on the same 619 strict Java mappings;
4. reporting complete-fix Coverage@k for k in {1, 3, 5, 10}.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MAPPING_DIR = ROOT / "mapping"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
K_VALUES = (1, 3, 5, 10)
EXPECTED_TOTAL = 619


def parse_operator_set(value: object) -> frozenset[str]:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        raise ValueError("Encountered an empty required-operator set.")
    return frozenset(part.strip() for part in text.split(";") if part.strip())


def coverage(required_sets: Iterable[frozenset[str]], selected: Iterable[str]) -> tuple[int, int, float]:
    sets = list(required_sets)
    selected_set = set(selected)
    covered = sum(required.issubset(selected_set) for required in sets)
    total = len(sets)
    return covered, total, 100.0 * covered / total


def main() -> None:
    frequencies = pd.read_csv(DATA_DIR / "prapr_published_mutator_frequencies.csv")
    mapping = pd.read_csv(MAPPING_DIR / "prapr_mapping_audit.csv")
    java = pd.read_csv(DATA_DIR / "strict_java_bug_operator_mappings.csv")

    if len(java) != EXPECTED_TOTAL:
        raise ValueError(f"Expected {EXPECTED_TOTAL} Java mappings, found {len(java)}.")
    if java["mapping_id"].nunique() != EXPECTED_TOTAL:
        raise ValueError("Java mapping_id values are not unique.")

    required_frequency_columns = {
        "published_rank", "prapr_id", "prapr_name", "hdrepair_frequency_percent"
    }
    required_mapping_columns = {
        "prapr_id", "mapped_family", "mapping_status", "mapping_rationale"
    }
    if not required_frequency_columns.issubset(frequencies.columns):
        raise ValueError("The PraPR frequency file is missing required columns.")
    if not required_mapping_columns.issubset(mapping.columns):
        raise ValueError("The mapping audit is missing required columns.")

    # Use the frequency table as the authoritative source and attach mappings.
    mapping_small = mapping[list(required_mapping_columns)].drop_duplicates("prapr_id")
    audit = frequencies.merge(mapping_small, on="prapr_id", how="left", validate="one_to_one")
    if audit["mapped_family"].isna().any():
        missing = audit.loc[audit["mapped_family"].isna(), "prapr_id"].tolist()
        raise ValueError(f"Unmapped PraPR mutators: {missing}")

    # Consolidate mutators mapped to the same unified family.
    ranking = (
        audit.groupby("mapped_family", as_index=False)
        .agg(
            aggregated_frequency_percent=("hdrepair_frequency_percent", "sum"),
            earliest_published_rank=("published_rank", "min"),
            contributing_mutators=("prapr_id", lambda values: ";".join(values)),
        )
        .sort_values(
            ["aggregated_frequency_percent", "earliest_published_rank", "mapped_family"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    ranking = ranking.rename(columns={"mapped_family": "operator"})
    ranking.to_csv(RESULTS_DIR / "prapr_mapped_ranking.csv", index=False)

    required_sets = java["operators"].map(parse_operator_set).tolist()
    order = ranking["operator"].tolist()

    result_rows = []
    membership_rows = []
    for k in K_VALUES:
        selected = order[:k]
        covered, total, percentage = coverage(required_sets, selected)
        result_rows.append(
            {
                "baseline": "PraPR published ranking after label mapping",
                "abstraction_level": "JVM bytecode (supplementary)",
                "target_language": "Java",
                "k": k,
                "operators": ";".join(selected),
                "covered": covered,
                "total": total,
                "coverage_percent": percentage,
            }
        )

    results = pd.DataFrame(result_rows)
    results.to_csv(RESULTS_DIR / "prapr_supplementary_comparison.csv", index=False)

    for row, required in zip(java.to_dict("records"), required_sets):
        membership_rows.append(
            {
                "mapping_id": row["mapping_id"],
                "project": row["project"],
                "bug_id": row["bug_id"],
                "required_operators": row["operators"],
                **{
                    f"covered_at_{k}": required.issubset(set(order[:k]))
                    for k in K_VALUES
                },
            }
        )
    pd.DataFrame(membership_rows).to_csv(
        RESULTS_DIR / "coverage_membership_by_bug.csv", index=False
    )

    metadata = {
        "eligible_java_mappings": EXPECTED_TOTAL,
        "k_values": list(K_VALUES),
        "mapped_order": order,
        "interpretation": (
            "Transferred-utility comparison; not a source-level baseline and not a "
            "reproduction of PraPR's end-to-end APR execution."
        ),
    }
    (RESULTS_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
