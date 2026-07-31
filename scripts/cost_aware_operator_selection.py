#!/usr/bin/env python3
"""
Cost-aware mutant-operator scheduling and selective invocation.

This script extends the existing RQ5 held-out evaluation by testing whether
operator selection improves when repair relevance and RQ3 search-space cost
are considered jointly.

Strategies under the same cost budget:
1. frequency              - descending training frequency
2. frequency_per_cost     - training frequency divided by RQ3 cost
3. cheap_first            - low-cost operators first
4. exact_cost_aware       - MILP portfolio maximizing training complete-fix
                            coverage subject to the cost budget
5. random                 - no-ranking baseline

Expected input:
    rq5_results/strict_bug_operator_mappings.csv
Required columns:
    language, project, operators
The operators column contains semicolon-separated canonical codes.

Default costs are transparent proxies derived from the RQ3 complexity tiers.
If operator_runtime_costs.csv (operator,cost) exists in BASE_DIR, a measured
cost scheme is evaluated as well.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix
from sklearn.model_selection import GroupKFold

# Reset any machine-level matplotlib configuration that may set an
# abnormally large font or DPI and trigger FreeType raster overflow.
plt.rcdefaults()
plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "figure.dpi": 100,
    "savefig.dpi": 180,
    "text.usetex": False,
})


# ---------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------

BASE_DIR = Path("path to directory/scripts").resolve()
INPUT_CANDIDATES = (
    BASE_DIR / "rq5_results" / "strict_bug_operator_mappings.csv",
    BASE_DIR / "strict_bug_operator_mappings.csv",
)
OUTPUT_DIR = BASE_DIR / "cost_aware_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MEASURED_COST_FILE = BASE_DIR / "operator_runtime_costs.csv"

N_SPLITS = 5
N_RANDOM_PORTFOLIOS = 1000
BOOTSTRAP_ITERATIONS = 5000
RANDOM_SEED = 20260322
BUDGET_FRACTIONS = (0.10, 0.20, 0.30, 0.40, 0.50)
PRIMARY_COST_SCHEME = "exponential"

CANONICAL_OPERATORS = (
    "CI", "MCR", "MRV", "LOR", "VA", "ROR", "MPM", "MOCS",
    "DOC", "SD", "MA", "AIS", "DTR", "CR", "SR", "EII", "VR",
    "CFSM", "SI", "BCO", "EI", "FLI", "WLI", "CASEI", "AA",
    "SM", "ElseI", "BR", "AOR", "DIS", "BWO", "RAR", "CN",
)

# RQ3 complexity labels reported in the manuscript.
OPERATOR_TIERS = {
    "MCR": "High", "CI": "Extremely High", "MRV": "Moderate",
    "LOR": "Low", "VA": "Extremely High", "MOCS": "Extremely High",
    "SI": "Moderate", "MPM": "High", "ROR": "Low", "SD": "Low",
    "DOC": "Low", "CR": "High", "MA": "High", "AIS": "Low",
    "SR": "Moderate", "DTR": "Moderate", "VR": "Moderate",
    "EII": "Moderate", "CFSM": "Moderate", "BCO": "Moderate",
    "EI": "Moderate", "FLI": "Moderate", "SM": "Low",
    "CASEI": "Moderate", "WLI": "Moderate", "AA": "Low",
    "AOR": "Low", "ElseI": "Low", "BWO": "Low", "RAR": "Low",
    "BR": "Low", "DIS": "Low", "CN": "Low",
}

# Sensitivity analysis avoids relying on one arbitrary numeric conversion.
TIER_COST_SCHEMES = {
    "linear": {
        "Low": 1.0, "Moderate": 2.0, "High": 3.0,
        "Extremely High": 4.0,
    },
    "exponential": {
        "Low": 1.0, "Moderate": 2.0, "High": 4.0,
        "Extremely High": 8.0,
    },
    "steep": {
        "Low": 1.0, "Moderate": 3.0, "High": 6.0,
        "Extremely High": 10.0,
    },
}

STRATEGIES = (
    "frequency", "frequency_per_cost", "cheap_first",
    "exact_cost_aware", "random",
)


# ---------------------------------------------------------------------
# 2. DATA LOADING
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class BugRecord:
    language: str
    project: str
    bug_id: str
    required: frozenset[str]


def find_input_file() -> Path:
    for candidate in INPUT_CANDIDATES:
        if candidate.is_file():
            return candidate
    attempted = "\n".join(f"  - {path}" for path in INPUT_CANDIDATES)
    raise FileNotFoundError(
        "Could not find strict_bug_operator_mappings.csv.\n"
        "Run the existing RQ5 cleaning/portfolio script first.\n"
        f"Locations checked:\n{attempted}"
    )


def parse_operator_set(value: object) -> frozenset[str]:
    if pd.isna(value):
        return frozenset()
    operators = {token.strip() for token in str(value).split(";") if token.strip()}
    unknown = operators - set(CANONICAL_OPERATORS)
    if unknown:
        raise ValueError(
            "Unknown operator labels in cleaned input: "
            + ", ".join(sorted(unknown))
        )
    return frozenset(operators)


def load_records(path: Path) -> list[BugRecord]:
    frame = pd.read_csv(path)
    frame.columns = [str(column).strip() for column in frame.columns]
    required_columns = {"language", "project", "operators"}
    missing = required_columns - set(frame.columns)
    if missing:
        raise ValueError(
            f"Missing columns in {path}: {sorted(missing)}. "
            f"Available: {list(frame.columns)}"
        )
    if "bug_id" not in frame.columns:
        frame["bug_id"] = [f"row-{index + 1}" for index in range(len(frame))]

    records: list[BugRecord] = []
    for row in frame.itertuples(index=False):
        required = parse_operator_set(getattr(row, "operators"))
        if not required:
            continue
        records.append(BugRecord(
            language=str(getattr(row, "language")).strip(),
            project=str(getattr(row, "project")).strip(),
            bug_id=str(getattr(row, "bug_id")).strip(),
            required=required,
        ))
    if not records:
        raise ValueError("No eligible bug-to-operator mappings were loaded.")
    return records


# ---------------------------------------------------------------------
# 3. COST MODELS
# ---------------------------------------------------------------------

def build_cost_schemes() -> dict[str, dict[str, float]]:
    schemes: dict[str, dict[str, float]] = {}
    for name, tier_costs in TIER_COST_SCHEMES.items():
        schemes[name] = {
            operator: float(tier_costs[OPERATOR_TIERS[operator]])
            for operator in CANONICAL_OPERATORS
        }

    if MEASURED_COST_FILE.is_file():
        measured = pd.read_csv(MEASURED_COST_FILE)
        measured.columns = [str(c).strip().lower() for c in measured.columns]
        if {"operator", "cost"} - set(measured.columns):
            raise ValueError(
                f"{MEASURED_COST_FILE} must contain columns operator,cost."
            )
        raw = {
            str(row.operator).strip(): float(row.cost)
            for row in measured.itertuples(index=False)
        }
        missing = set(CANONICAL_OPERATORS) - set(raw)
        if missing:
            raise ValueError(
                "Measured cost file is missing: " + ", ".join(sorted(missing))
            )
        if any(value <= 0 or not math.isfinite(value) for value in raw.values()):
            raise ValueError("All measured costs must be finite and > 0.")
        minimum = min(raw.values())
        schemes["measured"] = {
            operator: raw[operator] / minimum
            for operator in CANONICAL_OPERATORS
        }

    rows = []
    for scheme, costs in schemes.items():
        for operator in CANONICAL_OPERATORS:
            rows.append({
                "scheme": scheme,
                "operator": operator,
                "tier": OPERATOR_TIERS[operator],
                "cost": costs[operator],
            })
    pd.DataFrame(rows).to_csv(
        OUTPUT_DIR / "operator_cost_table.csv", index=False
    )
    return schemes


# ---------------------------------------------------------------------
# 4. SELECTION METHODS
# ---------------------------------------------------------------------

def operator_frequency(records: Sequence[BugRecord]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record.required)
    return counts


def select_from_ranking(
    ranking: Sequence[str], costs: dict[str, float], budget: float
) -> tuple[str, ...]:
    selected: list[str] = []
    spent = 0.0
    for operator in ranking:
        cost = costs[operator]
        if spent + cost <= budget + 1e-9:
            selected.append(operator)
            spent += cost
    return tuple(selected)


def frequency_ranking(train: Sequence[BugRecord]) -> tuple[str, ...]:
    frequency = operator_frequency(train)
    return tuple(sorted(
        CANONICAL_OPERATORS,
        key=lambda operator: (-frequency[operator], operator),
    ))


def frequency_per_cost_ranking(
    train: Sequence[BugRecord], costs: dict[str, float]
) -> tuple[str, ...]:
    frequency = operator_frequency(train)
    return tuple(sorted(
        CANONICAL_OPERATORS,
        key=lambda operator: (
            -(frequency[operator] / costs[operator]),
            -frequency[operator], costs[operator], operator,
        ),
    ))


def cheap_first_ranking(
    train: Sequence[BugRecord], costs: dict[str, float]
) -> tuple[str, ...]:
    frequency = operator_frequency(train)
    return tuple(sorted(
        CANONICAL_OPERATORS,
        key=lambda operator: (costs[operator], -frequency[operator], operator),
    ))


def exact_cost_aware_portfolio(
    train: Sequence[BugRecord], costs: dict[str, float], budget: float
) -> tuple[str, ...]:
    """Maximize training complete-fix coverage under a total cost budget."""
    operators = list(CANONICAL_OPERATORS)
    op_index = {operator: index for index, operator in enumerate(operators)}
    n_ops = len(operators)
    n_bugs = len(train)
    n_vars = n_ops + n_bugs

    frequency = operator_frequency(train)
    max_frequency = max(frequency.values(), default=1)

    # scipy.milp minimizes; negative coefficients maximize.
    objective = np.zeros(n_vars, dtype=float)
    objective[n_ops:] = -1.0
    for operator, index in op_index.items():
        objective[index] = -1e-5 * (frequency[operator] / max_frequency)

    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    row = 0

    # A bug can be covered only if every required operator is selected.
    for bug_index, record in enumerate(train):
        y_index = n_ops + bug_index
        for operator in record.required:
            row_indices.extend((row, row))
            column_indices.extend((y_index, op_index[operator]))
            values.extend((1.0, -1.0))
            lower.append(-np.inf)
            upper.append(0.0)
            row += 1

    # Total selected operator cost cannot exceed the budget.
    for operator, index in op_index.items():
        row_indices.append(row)
        column_indices.append(index)
        values.append(costs[operator])
    lower.append(-np.inf)
    upper.append(budget)
    row += 1

    matrix = csr_matrix(
        (values, (row_indices, column_indices)),
        shape=(row, n_vars),
    )
    result = milp(
        c=objective,
        integrality=np.ones(n_vars, dtype=int),
        bounds=Bounds(np.zeros(n_vars), np.ones(n_vars)),
        constraints=LinearConstraint(
            matrix, lb=np.array(lower), ub=np.array(upper)
        ),
        options={"time_limit": 120.0},
    )
    if result.x is None or not result.success:
        raise RuntimeError(
            "Cost-aware optimization failed: "
            f"status={result.status}; message={result.message}"
        )

    selected = [
        operator for operator, index in op_index.items()
        if result.x[index] >= 0.5
    ]
    # Invocation order inside the chosen portfolio.
    selected.sort(key=lambda operator: (
        -(frequency[operator] / costs[operator]),
        -frequency[operator], operator,
    ))
    return tuple(selected)


def random_portfolio(
    costs: dict[str, float], budget: float, rng: random.Random
) -> tuple[str, ...]:
    ranking = list(CANONICAL_OPERATORS)
    rng.shuffle(ranking)
    return select_from_ranking(ranking, costs, budget)


def is_covered(record: BugRecord, selected: Iterable[str]) -> int:
    return int(record.required.issubset(set(selected)))


def portfolio_cost(selected: Iterable[str], costs: dict[str, float]) -> float:
    return float(sum(costs[operator] for operator in selected))


# ---------------------------------------------------------------------
# 5. PROJECT-LEVEL HELD-OUT EVALUATION
# ---------------------------------------------------------------------

def evaluate() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    input_file = find_input_file()
    records = load_records(input_file)
    cost_schemes = build_cost_schemes()
    print(f"Loaded {len(records)} mappings from {input_file}")

    result_rows: list[dict[str, object]] = []
    portfolio_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []

    for language in sorted({record.language for record in records}):
        language_records = [r for r in records if r.language == language]
        projects = sorted({r.project for r in language_records})
        n_splits = min(N_SPLITS, len(projects))
        if n_splits < 2:
            raise ValueError(f"{language} needs at least two projects.")

        indices = np.arange(len(language_records))
        groups = np.array([r.project for r in language_records])
        splitter = GroupKFold(n_splits=n_splits)

        for fold, (train_idx, test_idx) in enumerate(
            splitter.split(indices, groups=groups), start=1
        ):
            train = [language_records[i] for i in train_idx]
            test = [language_records[i] for i in test_idx]

            for scheme_name, costs in cost_schemes.items():
                total_cost = sum(costs.values())
                for budget_fraction in BUDGET_FRACTIONS:
                    budget = max(
                        min(costs.values()),
                        round(total_cost * budget_fraction, 6),
                    )

                    selections = {
                        "frequency": select_from_ranking(
                            frequency_ranking(train), costs, budget
                        ),
                        "frequency_per_cost": select_from_ranking(
                            frequency_per_cost_ranking(train, costs),
                            costs, budget,
                        ),
                        "cheap_first": select_from_ranking(
                            cheap_first_ranking(train, costs), costs, budget
                        ),
                        "exact_cost_aware": exact_cost_aware_portfolio(
                            train, costs, budget
                        ),
                    }

                    for strategy, selected in selections.items():
                        vector = [is_covered(record, selected) for record in test]
                        covered = int(sum(vector))
                        total = len(test)
                        coverage = 100.0 * covered / total if total else math.nan
                        selected_cost = portfolio_cost(selected, costs)

                        result_rows.append({
                            "language": language,
                            "fold": fold,
                            "cost_scheme": scheme_name,
                            "budget_fraction": budget_fraction,
                            "budget": budget,
                            "strategy": strategy,
                            "covered": covered,
                            "total": total,
                            "coverage_percent": coverage,
                            "selected_count": len(selected),
                            "selected_cost": selected_cost,
                        })
                        portfolio_rows.append({
                            "language": language,
                            "fold": fold,
                            "cost_scheme": scheme_name,
                            "budget_fraction": budget_fraction,
                            "budget": budget,
                            "strategy": strategy,
                            "selected_count": len(selected),
                            "selected_cost": selected_cost,
                            "selected_operators": ";".join(selected),
                        })
                        for record, prediction in zip(test, vector):
                            prediction_rows.append({
                                "language": language,
                                "fold": fold,
                                "cost_scheme": scheme_name,
                                "budget_fraction": budget_fraction,
                                "budget": budget,
                                "strategy": strategy,
                                "project": record.project,
                                "bug_id": record.bug_id,
                                "required_operators": ";".join(
                                    sorted(record.required)
                                ),
                                "covered": prediction,
                            })

                    # Random no-ranking baseline.
                    rng = random.Random(
                        RANDOM_SEED + fold * 100000
                        + int(budget_fraction * 10000)
                        + sum(ord(c) for c in language + scheme_name)
                    )
                    random_coverages: list[float] = []
                    random_counts: list[int] = []
                    random_costs: list[float] = []
                    per_bug_probability = np.zeros(len(test), dtype=float)

                    for _ in range(N_RANDOM_PORTFOLIOS):
                        selected = random_portfolio(costs, budget, rng)
                        vector = np.array(
                            [is_covered(record, selected) for record in test],
                            dtype=float,
                        )
                        per_bug_probability += vector
                        random_coverages.append(
                            100.0 * float(vector.mean()) if len(vector) else math.nan
                        )
                        random_counts.append(len(selected))
                        random_costs.append(portfolio_cost(selected, costs))

                    per_bug_probability /= N_RANDOM_PORTFOLIOS
                    result_rows.append({
                        "language": language,
                        "fold": fold,
                        "cost_scheme": scheme_name,
                        "budget_fraction": budget_fraction,
                        "budget": budget,
                        "strategy": "random",
                        "covered": (
                            float(np.mean(random_coverages)) * len(test) / 100.0
                        ),
                        "total": len(test),
                        "coverage_percent": float(np.mean(random_coverages)),
                        "selected_count": float(np.mean(random_counts)),
                        "selected_cost": float(np.mean(random_costs)),
                        "coverage_std": float(
                            np.std(random_coverages, ddof=1)
                        ),
                    })
                    portfolio_rows.append({
                        "language": language,
                        "fold": fold,
                        "cost_scheme": scheme_name,
                        "budget_fraction": budget_fraction,
                        "budget": budget,
                        "strategy": "random",
                        "selected_count": float(np.mean(random_counts)),
                        "selected_cost": float(np.mean(random_costs)),
                        "selected_operators": (
                            f"Mean of {N_RANDOM_PORTFOLIOS} random portfolios"
                        ),
                    })
                    for record, probability in zip(test, per_bug_probability):
                        prediction_rows.append({
                            "language": language,
                            "fold": fold,
                            "cost_scheme": scheme_name,
                            "budget_fraction": budget_fraction,
                            "budget": budget,
                            "strategy": "random",
                            "project": record.project,
                            "bug_id": record.bug_id,
                            "required_operators": ";".join(
                                sorted(record.required)
                            ),
                            "covered": probability,
                        })

    results = pd.DataFrame(result_rows)
    portfolios = pd.DataFrame(portfolio_rows)
    predictions = pd.DataFrame(prediction_rows)
    results.to_csv(OUTPUT_DIR / "heldout_results.csv", index=False)
    portfolios.to_csv(OUTPUT_DIR / "selected_portfolios.csv", index=False)
    predictions.to_csv(
        OUTPUT_DIR / "out_of_fold_predictions.csv", index=False
    )
    return results, portfolios, predictions


# ---------------------------------------------------------------------
# 6. SUMMARIES AND PAIRED COMPARISONS
# ---------------------------------------------------------------------

def weighted_summary(results: pd.DataFrame) -> pd.DataFrame:
    frame = results.copy()
    frame["weighted_covered"] = (
        frame["coverage_percent"] / 100.0 * frame["total"]
    )
    summary = (
        frame.groupby(
            ["language", "cost_scheme", "budget_fraction", "strategy"],
            as_index=False,
        )
        .agg(
            covered=("weighted_covered", "sum"),
            total=("total", "sum"),
            mean_selected_count=("selected_count", "mean"),
            mean_selected_cost=("selected_cost", "mean"),
        )
    )
    summary["coverage_percent"] = (
        100.0 * summary["covered"] / summary["total"]
    )
    summary.to_csv(OUTPUT_DIR / "heldout_summary.csv", index=False)
    return summary


def paired_bootstrap(
    values_a: np.ndarray,
    values_b: np.ndarray,
    iterations: int,
    seed: int,
) -> tuple[float, float, float]:
    if len(values_a) != len(values_b):
        raise ValueError("Paired vectors must have equal length.")
    if len(values_a) == 0:
        return math.nan, math.nan, math.nan
    observed = 100.0 * float(np.mean(values_a - values_b))
    rng = np.random.default_rng(seed)
    sample_indices = rng.integers(
        0, len(values_a), size=(iterations, len(values_a))
    )
    samples = 100.0 * np.mean(
        values_a[sample_indices] - values_b[sample_indices], axis=1
    )
    low, high = np.percentile(samples, [2.5, 97.5])
    return observed, float(low), float(high)


def make_paired_comparisons(predictions: pd.DataFrame) -> pd.DataFrame:
    pairs = (
        ("frequency_per_cost", "frequency"),
        ("exact_cost_aware", "frequency"),
        ("exact_cost_aware", "frequency_per_cost"),
        ("frequency", "cheap_first"),
    )
    rows: list[dict[str, object]] = []
    for keys, group in predictions.groupby(
        ["language", "cost_scheme", "budget_fraction"]
    ):
        language, scheme, budget_fraction = keys
        deterministic = group[group["strategy"] != "random"]
        pivot = deterministic.pivot_table(
            index=["project", "bug_id"],
            columns="strategy",
            values="covered",
            aggfunc="first",
        )
        for strategy_a, strategy_b in pairs:
            if strategy_a not in pivot or strategy_b not in pivot:
                continue
            paired = pivot[[strategy_a, strategy_b]].dropna()
            difference, low, high = paired_bootstrap(
                paired[strategy_a].to_numpy(dtype=float),
                paired[strategy_b].to_numpy(dtype=float),
                BOOTSTRAP_ITERATIONS,
                RANDOM_SEED + int(budget_fraction * 10000)
                + sum(ord(c) for c in language + scheme),
            )
            rows.append({
                "language": language,
                "cost_scheme": scheme,
                "budget_fraction": budget_fraction,
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
                "paired_bugs": len(paired),
                "difference_percentage_points": difference,
                "ci_95_low": low,
                "ci_95_high": high,
            })
    comparisons = pd.DataFrame(rows)
    comparisons.to_csv(OUTPUT_DIR / "paired_comparisons.csv", index=False)
    return comparisons


# ---------------------------------------------------------------------
# 7. PLOTS AND REPORT
# ---------------------------------------------------------------------

def make_plots(summary: pd.DataFrame) -> None:
    primary = summary[summary["cost_scheme"] == PRIMARY_COST_SCHEME]
    for language, group in primary.groupby("language"):
        fig, axis = plt.subplots(figsize=(7.2, 4.8), dpi=100)
        try:
            for strategy in STRATEGIES:
                rows = group[group["strategy"] == strategy].sort_values(
                    "budget_fraction"
                )
                if rows.empty:
                    continue
                axis.plot(
                    100.0 * rows["budget_fraction"],
                    rows["coverage_percent"],
                    marker="o",
                    label=strategy.replace("_", " "),
                )

            axis.set_xlabel(
                "Search-cost budget (% of taxonomy cost)", fontsize=10
            )
            axis.set_ylabel(
                "Held-out complete-fix coverage (%)", fontsize=10
            )
            axis.set_title(
                f"Cost-aware operator selection: {language}", fontsize=11
            )
            axis.tick_params(axis="both", labelsize=9)
            axis.legend(fontsize=8)
            axis.grid(True, alpha=0.25)
            fig.tight_layout()

            safe_language = "".join(
                character if character.isalnum() else "_"
                for character in str(language).lower()
            )

            # SVG is retained as a vector fallback and avoids dependence on
            # high-resolution glyph rasterization.
            fig.savefig(
                OUTPUT_DIR / f"coverage_{safe_language}.svg",
                format="svg",
                bbox_inches="tight",
            )

            try:
                fig.savefig(
                    OUTPUT_DIR / f"coverage_{safe_language}.png",
                    format="png",
                    dpi=180,
                    bbox_inches="tight",
                )
            except RuntimeError as error:
                print(
                    f"Warning: PNG export failed for {language}: {error}. "
                    "The SVG plot was still saved."
                )
        finally:
            plt.close(fig)


def write_report(
    summary: pd.DataFrame, comparisons: pd.DataFrame
) -> None:
    primary = summary[summary["cost_scheme"] == PRIMARY_COST_SCHEME]
    lines = [
        "COST-AWARE MUTANT-OPERATOR SELECTION",
        "=" * 44,
        "",
        "Primary proxy: exponential tier costs ",
        "(Low=1, Moderate=2, High=4, Extremely High=8).",
        "Linear and steep mappings are included as sensitivity checks.",
        "",
        "Interpretation:",
        "- frequency: current baseline",
        "- frequency_per_cost: cost-aware scheduling",
        "- exact_cost_aware: selective invocation under a cost budget",
        "- cheap_first: tests whether simple operators alone are sufficient",
        "- random: no-ranking baseline",
        "",
        "IMPORTANT LIMITATION:",
        "The default tier costs are structural proxies, not measured runtime.",
        "Runtime claims require operator-level timing or candidate-count data.",
        "Supply operator_runtime_costs.csv to evaluate measured costs.",
        "",
        "PRIMARY-SCHEME SUMMARY",
        "-" * 44,
        primary[[
            "language", "budget_fraction", "strategy",
            "coverage_percent", "mean_selected_count",
            "mean_selected_cost",
        ]].sort_values(
            ["language", "budget_fraction", "strategy"]
        ).to_string(index=False, float_format=lambda value: f"{value:.2f}"),
        "",
        "PAIRED BOOTSTRAP COMPARISONS",
        "-" * 44,
    ]
    primary_comparisons = comparisons[
        comparisons["cost_scheme"] == PRIMARY_COST_SCHEME
    ]
    if primary_comparisons.empty:
        lines.append("No comparisons produced.")
    else:
        lines.append(primary_comparisons.sort_values(
            ["language", "budget_fraction", "strategy_a", "strategy_b"]
        ).to_string(index=False, float_format=lambda value: f"{value:.2f}"))

    (OUTPUT_DIR / "README_RESULTS.txt").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    primary.to_csv(
        OUTPUT_DIR / "primary_scheme_summary.csv", index=False
    )


def main() -> None:
    results, _, predictions = evaluate()
    summary = weighted_summary(results)
    comparisons = make_paired_comparisons(predictions)

    # Write the numerical outputs before plotting, so a local font/rendering
    # problem can never discard or hide the completed empirical results.
    write_report(summary, comparisons)
    make_plots(summary)
    print("\nAnalysis completed.")
    print(f"Results: {OUTPUT_DIR}")
    print(
        "Start with primary_scheme_summary.csv, "
        "paired_comparisons.csv, and README_RESULTS.txt."
    )


if __name__ == "__main__":
    main()
