"""
RQ5 redesign: source-level operator portfolio selection

This script implements the supervisor-requested comparison:
1. Frequency-based source-level operator portfolio (baseline)
2. Exact composition-aware source-level portfolio (proposed)
3. Random source-level portfolio (sanity baseline)
4. Optional published source-level rankings supplied by the researcher
5. Optional PraPR mapped ranking, reported only as a supplementary
   cross-abstraction comparison

Important:
- The script measures complete-fix representability, not actual APR success.
- Rankings/portfolios are learned only from training projects and evaluated
  on held-out projects.
- The proposed method selects the best size-k portfolio directly; it does
  not claim a new frequency-ranking algorithm.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Sequence, Set, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix
from sklearn.model_selection import GroupKFold


# ---------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------

BASE_DIR = Path("/home1/furqan/my_mutation_experiments/scripts").resolve()


def find_input_file(patterns: tuple[str, ...], label: str) -> Path:
    """Find one dataset file in BASE_DIR using exact or wildcard names."""
    matches: list[Path] = []

    for pattern in patterns:
        matches.extend(
            path for path in BASE_DIR.glob(pattern)
            if path.is_file()
        )

    # Remove duplicates while preserving deterministic order.
    unique_matches = sorted(set(matches), key=lambda path: path.name.lower())

    if not unique_matches:
        available = "\n".join(
            f"  - {path.name}" for path in sorted(BASE_DIR.iterdir())
            if path.is_file()
        )
        raise FileNotFoundError(
            f"Could not find the {label} dataset in {BASE_DIR}.\n"
            f"Patterns tried: {patterns}\n"
            f"Available files:\n{available or '  (no files found)'}"
        )

    if len(unique_matches) > 1:
        names = "\n".join(f"  - {path.name}" for path in unique_matches)
        raise RuntimeError(
            f"Multiple possible {label} dataset files were found:\n{names}\n"
            "Rename the intended file uniquely or set its exact path."
        )

    return unique_matches[0]


JAVA_FILE = BASE_DIR / "Defects4j_full.xlsx"
PYTHON_FILE = BASE_DIR / "BugInPy.xlsx"

JAVASCRIPT_FILE = BASE_DIR / "bugjs_manual(1).csv"


OUTPUT_DIR = BASE_DIR / "rq5_results_corrected_audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_BASELINE_FILE = BASE_DIR / "source_level_baselines.csv"
PRAPR_FILE = BASE_DIR / "prapr_mapped_ranking.csv"

print("Using input files:")
print(f"  Java      : {JAVA_FILE}")
print(f"  Python    : {PYTHON_FILE}")
print(f"  JavaScript: {JAVASCRIPT_FILE}")

K_VALUES = (1, 3, 5, 10)
N_SPLITS = 5
N_RANDOM_PORTFOLIOS = 1000
RANDOM_SEED = 42

# Expected strict-eligible counts reported in the current manuscript.
# A mismatch is reported for audit; the script does not silently force it.
EXPECTED_COUNTS = {"Java": 633, "Python": 194, "JavaScript": 128}

# Optional external baseline files.
#
# source_level_baselines.csv columns:
# baseline,language,rank,operator
#
# Example:
# PriorSourceMethod,Java,1,ROR
# PriorSourceMethod,Java,2,AOR
#
# Use language="ALL" for a language-independent published ranking.
# SOURCE_BASELINE_FILE is configured above using BASE_DIR

# PraPR is supplementary only because it is a bytecode-level mutator ranking.
# prapr_mapped_ranking.csv columns:
# rank,operator
# PRAPR_FILE is configured above using BASE_DIR


# ---------------------------------------------------------------------
# 2. CANONICAL SOURCE-LEVEL TAXONOMY AND LABEL NORMALIZATION
# ---------------------------------------------------------------------

CANONICAL_OPERATORS = {
    "CI", "MCR", "MRV", "LOR", "VA", "ROR", "MPM", "MOCS",
    "DOC", "SD", "MA", "AIS", "DTR", "CR", "SR", "EII", "VR",
    "CFSM", "SI", "BCO", "EI", "FLI", "WLI", "CASEI", "AA",
    "SM", "ElseI", "BR", "AOR", "DIS", "BWO", "RAR", "CN",
}

# Explicit non-canonical codes observed in the manual mappings.
# Only semantically unambiguous aliases are normalized automatically.
EXTRA_OPERATOR_CODES = {
    "MCI", "MCD", "MNM", "CFS", "CFD", "DS", "DOM", "COR",
    "LD", "SMRO", "SLR", "IOR", "EXI", "SRO",
    # Ambiguous codes retained for audit rather than silently mapped:
    "VI", "CA", "CC", "ER", "TAR", "MBR", "LI", "AI",
}

SAFE_ALIAS_MAP: Dict[str, str] = {
    "MCI": "MCR",       # Method Call Insertion
    "MCD": "MCR",       # Method Call Deletion
    "MNM": "MCR",       # Method Name Modification
    "CFS": "CFSM",      # Control Flow Statement
    "CFD": "CFSM",      # Control Flow Deletion/Modification
    "DS": "SD",         # Delete Statement
    "DOM": "MA",        # Deletion of Method (inverse of method addition)
    "COR": "ROR",       # Conditional Operator Replacement
    "LD": "WLI",        # Loop deletion family
    "SMRO": "SM",       # String Manipulation Replacement
    "SLR": "SM",        # String Literal Replacement
    "IOR": "AOR",       # Increment/Decrement Operator Replacement
    "EXI": "EI",        # Exception Insertion spelling variant
    "SRO": "SR",        # Statement Reordering Operator
}

ALL_EXPLICIT_CODES = sorted(
    {operator.upper() for operator in CANONICAL_OPERATORS}
    | EXTRA_OPERATOR_CODES,
    key=len,
    reverse=True,
)

EXPLICIT_CODE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])("
    + "|".join(map(re.escape, ALL_EXPLICIT_CODES))
    + r")(?:0)?(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# Regex patterns for verbose and misspelled labels.
PHRASE_PATTERNS: Sequence[Tuple[str, str]] = (
    (r"\bcondition\s+(?:insertion|inserion)\b", "CI"),
    (r"\bcondtion\s+insertion\b|\bcondotion\s+insertion\b", "CI"),
    (r"\bcondition\s+(?:deletion|removal|remval)\b", "DOC"),

    (r"\bmethod\s*call(?:ed)?\s+(?:replacement|replacment|replacemet|"
     r"replacenemt|replacementy|recplacement|replecement)\b", "MCR"),
    (r"\bmethodcall\s+replacement\b|\bmethodcalled\s+replacement\b", "MCR"),
    (r"\bmethod\s*call\s+(?:insertion|deletion|removal)\b", "MCR"),
    (r"\bmethodcall\s+insertion\b", "MCR"),

    (r"\bmodif(?:ication|cation)\s+of\s+(?:the\s+)?return\s+value\b", "MRV"),
    (r"\bmodification\s+return\s+value\b|\breturn\s+value\s+modification\b|"
     r"\bretern\s+value\s+modification\b", "MRV"),

    (r"\bmodification\s+of\s+(?:condition|condtion|concition|consition)\s+"
     r"(?:statement|ststement|stement|stetement)?\b", "MOCS"),
    (r"\bmodification\s+condition\s+statement\b|"
     r"\bmodification\s+of\s+condition\b", "MOCS"),

    (r"\blogical\s+(?:operator|oeprator)\s+replacement\b", "LOR"),
    (r"\brelational\s+operator\s+replacement\b", "ROR"),

    (r"\bvariable\s+assignment\b|\bvariable\s+assignement\b|"
     r"\bvariable\s+(?:initialization|initialzation|initization|"
     r"initilzation|initiozation|insertion)\b|"
     r"\bassignment\s+insertion\b", "VA"),
    (r"\bvariable\s+replacement\b", "VR"),

    (r"\bmethod\s+parameters?\s+modification\b", "MPM"),

    (r"\bstatement\s+insertion\b|\bstatemet\s+insertion\b|"
     r"\bsatatement\s+insertion\b|\bstatament\s+insertion\b|"
     r"\bstatment\s+insertion\b", "SI"),
    (r"\bstatement\s+deletion\b|\bstatament\s+deletion\b|"
     r"\bstatment\s+deletion\b", "SD"),
    (r"\bstatement\s+(?:reorder|reordering)\b", "SR"),

    (r"\bmethod\s+addition\b", "MA"),
    (r"\b(?:add|addition\s+of)\s+import(?:a)?\s+statement\b|"
     r"\bimport\s+statement\s+addition\b|\badd\s+import\s+statement\b", "AIS"),
    (r"\bimport\s+statement\s+deletion\b", "DIS"),

    (r"\bdata\s*type\s+replacement\b|\bdatatype\s+replacement\b|"
     r"\btype\s+(?:annotation|annottation)\s+replacement\b", "DTR"),
    (r"\bconstant\s+replacementy?\b", "CR"),

    (r"\belse[\s-]*if\s+insertion\b", "EII"),
    (r"\belse\s+(?:insertion|inserion)\b", "ElseI"),

    (r"\bcontrol\s+flow(?:\s+statement)?"
     r"(?:\s+(?:modification|deletion))?\b", "CFSM"),
    (r"\bboundary\s+condition\s+operator\b", "BCO"),

    (r"\bexception\s+insertion\b|\bexecption\s+insertion\b", "EI"),
    (r"\bfor\s+loop\s+insertion\b", "FLI"),
    (r"\bwhile\s+loop\s+insertion\b", "WLI"),
    (r"\bcase\s+insertion\b", "CASEI"),
    (r"\bannotation\s+addition\b", "AA"),

    (r"\bstring\s+(?:replacement|modification)\b|"
     r"\bsubstring\s+modification\b", "SM"),
    (r"\bbracket\s+reordering\b", "BR"),
    (r"\b(?:arithmetic|arthematic)\s+operator\s+replacement\b", "AOR"),
    (r"\bbitwise\s+operator\s+replacement\b", "BWO"),
    (r"\breference\s+assignment\s+replacement\b", "RAR"),
    (r"\bcondition\s+negation\b", "CN"),
)

# These concepts are not automatically forced into the taxonomy.
# They are excluded from the strict set until manually resolved.
AMBIGUOUS_PATTERNS: Sequence[str] = (
    r"\bexpression\s+replacement\b",
    r"\bconstant\s+assertion\b",
    r"\bmethod\s+body\s+replacement\b",
    r"\bcollection[\s-]+construction\b",
    r"\bstatement\s+replacement\b",
)


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def extract_explicit_codes(value: object) -> List[str]:
    """Extract canonical and known non-canonical abbreviations."""
    raw = normalize_text(value)
    result: List[str] = []

    for match in EXPLICIT_CODE_PATTERN.finditer(raw):
        code = match.group(1).upper()
        if code == "ELSEI":
            code = "ElseI"
        if code not in result:
            result.append(code)

    return result


def extract_phrase_codes(value: object) -> List[str]:
    """Use descriptive labels only when no explicit code is available."""
    lower = normalize_text(value).lower()
    result: List[str] = []

    for pattern, canonical in PHRASE_PATTERNS:
        if re.search(pattern, lower) and canonical not in result:
            result.append(canonical)

    return result


def parse_operator_set(
    primary_value: object,
    secondary_value: object = "",
) -> Tuple[FrozenSet[str], Tuple[str, ...]]:
    """
    Parse one manual mapping.

    Explicit codes in the dataset-specific primary column are preferred.
    The secondary column and phrase matching are used only as fallbacks.
    Ambiguous non-canonical codes are retained in ``unresolved`` and the
    corresponding row is excluded from the strict RQ5 evaluation.
    """
    primary = normalize_text(primary_value)
    secondary = normalize_text(secondary_value)

    if (
        primary.lower() in {"", "no", "none", "nan", "no operator"}
        and secondary.lower() in {"", "no", "none", "nan", "no operator"}
    ):
        return frozenset(), tuple()

    codes = extract_explicit_codes(primary)
    if not codes:
        codes = extract_explicit_codes(secondary)
    if not codes:
        codes = extract_phrase_codes(primary)
    if not codes:
        codes = extract_phrase_codes(secondary)

    canonical: Set[str] = set()
    unresolved: Set[str] = set()

    for code in codes:
        normalized = SAFE_ALIAS_MAP.get(code.upper(), code)
        if normalized in CANONICAL_OPERATORS:
            canonical.add(normalized)
        else:
            unresolved.add(code.upper())

    return frozenset(sorted(canonical)), tuple(sorted(unresolved))


# ---------------------------------------------------------------------
# 3. LOAD AND CLEAN THE THREE DATASETS
# ---------------------------------------------------------------------

JAVA_PROJECT_ALIASES: Dict[str, str] = {
    "cli": "Cli",
    "csv": "Csv",
    "codec": "Codec",
    "gson": "Gson",
    "chart": "Chart",
    "ch": "Chart",
    "collection": "Collections",
    "collections": "Collections",
    "closure": "Closure",
    "closoure": "Closure",
    "compress": "Compress",
    "jacksoncore": "JacksonCore",
    "jacksondatabind": "JacksonDatabind",
    "jacksonxml": "JacksonXml",
    "jxpath": "JxPath",
    "lang": "Lang",
    "math": "Math",
    "mockito": "Mockito",
    "mokito": "Mockito",
    "time": "Time",
}


def normalize_java_project_prefix(prefix: str) -> str:
    cleaned = prefix.lower().replace("_4j", "").strip("_-")
    return JAVA_PROJECT_ALIASES.get(cleaned, prefix.strip("_-"))


def derive_java_projects(df: pd.DataFrame) -> pd.Series:
    """
    Recover project membership from ordered Defects4J BugIDs.

    The first row of each project contains a textual project prefix, while
    many subsequent rows contain only numeric bug IDs. The detected project
    is therefore carried forward until a new textual prefix appears.
    """
    projects: List[str] = []
    current_project = ""

    for bug_id, project_hint in zip(
        df["BugID"].tolist(),
        df["Bug identification"].tolist(),
    ):
        bug_text = normalize_text(bug_id)
        match = re.match(r"([A-Za-z][A-Za-z_-]*)", bug_text)

        if match:
            current_project = normalize_java_project_prefix(match.group(1))
        elif not current_project:
            hint = normalize_text(project_hint)
            hint_match = re.search(
                r"(Cli|Csv|Codec|Gson|Chart|Collections?|Closure|Compress|"
                r"JacksonCore|JacksonDatabind|JacksonXml|JxPath|Lang|Math|"
                r"Mockito|Time)",
                hint,
                re.IGNORECASE,
            )
            if hint_match:
                current_project = normalize_java_project_prefix(
                    hint_match.group(1)
                )

        projects.append(current_project or "UnknownProject")

    return pd.Series(projects, index=df.index, dtype="object")


def find_column(df: pd.DataFrame, alternatives: Sequence[str]) -> str:
    normalized = {
        re.sub(r"[^a-z0-9]+", "", str(column).lower()): str(column)
        for column in df.columns
    }

    for candidate in alternatives:
        key = re.sub(r"[^a-z0-9]+", "", candidate.lower())
        if key in normalized:
            return normalized[key]

    raise ValueError(
        f"None of the required columns {list(alternatives)} were found. "
        f"Available columns: {list(df.columns)}"
    )


def load_dataset(
    path: Path,
    language: str,
    primary_operator_columns: Sequence[str],
    secondary_operator_columns: Sequence[str],
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)

    df.columns = [str(column).strip() for column in df.columns]

    bug_id_column = find_column(df, ["BugID", "Bug ID"])
    project_column = find_column(
        df, ["Bug identification", "Project", "Project name"]
    )
    primary_column = find_column(df, primary_operator_columns)
    secondary_column = find_column(df, secondary_operator_columns)

    # Standard internal names used by the project derivation logic.
    df = df.rename(
        columns={
            bug_id_column: "BugID",
            project_column: "Bug identification",
        }
    )

    if language == "Java":
        project = derive_java_projects(df)

        # Jsoup uses the Bug identification column for numeric bug IDs.
        jsoup_mask = (
            pd.Series(project, index=df.index)
            .astype(str).str.strip().str.lower().eq("jsoup")
        )

        if jsoup_mask.any():
            jsoup_ids = pd.to_numeric(
                df.loc[jsoup_mask, "Bug identification"],
                errors="coerce"
            )

            if (
                jsoup_ids.isna().any()
                or not (jsoup_ids % 1 == 0).all()
            ):
                raise ValueError("Invalid Jsoup bug IDs")

            df.loc[jsoup_mask, "BugID"] = (
                "Jsoup-" + jsoup_ids.astype(int).astype(str)
            )
    else:
        project = (
            df["Bug identification"]
            .ffill()
            .map(normalize_text)
            .replace("", "UnknownProject")
        )

    parsed = [
        parse_operator_set(primary, secondary)
        for primary, secondary in zip(
            df[primary_column].tolist(),
            df[secondary_column].tolist(),
        )
    ]

    primary_values = df[primary_column].map(normalize_text)
    secondary_values = df[secondary_column].map(normalize_text)

    cleaned = pd.DataFrame({
        "language": language,
        "project": project,
        "bug_id": df["BugID"].map(normalize_text),
        "primary_operator_column": primary_column,
        "secondary_operator_column": secondary_column,
        "raw_primary_mapping": primary_values,
        "raw_secondary_mapping": secondary_values,
        "raw_mapping": primary_values + " || " + secondary_values,
        "operator_set": [item[0] for item in parsed],
        "unresolved": [item[1] for item in parsed],
    })

    no_values = {"", "no", "none", "nan", "no operator"}
    cleaned["is_no_operator"] = (
        cleaned["raw_primary_mapping"].str.lower().isin(no_values)
        & cleaned["raw_secondary_mapping"].str.lower().isin(no_values)
    )
    cleaned["strict_eligible"] = (
        ~cleaned["is_no_operator"]
        & cleaned["operator_set"].map(bool)
        & cleaned["unresolved"].map(lambda values: len(values) == 0)
    )
    cleaned["operators"] = cleaned["operator_set"].map(
        lambda values: ";".join(sorted(values))
    )
    cleaned["unresolved_labels"] = cleaned["unresolved"].map(
        lambda values: ";".join(values)
    )
    cleaned["mapping_id"] = (
        cleaned["language"] + "::"
        + cleaned["project"] + "::"
        + cleaned["bug_id"]
    )

    return cleaned


def load_all_data() -> pd.DataFrame:
    frames = [
        # Java's canonical abbreviations are in Mutant ID.
        load_dataset(
            JAVA_FILE,
            "Java",
            ["Mutant ID"],
            ["Munatnt Operator", "Mutant Operator"],
        ),
        # Python and JavaScript use the operator-code column as primary.
        load_dataset(
            PYTHON_FILE,
            "Python",
            ["Munatnt Operator", "Mutant Operator"],
            ["Mutant ID"],
        ),
        load_dataset(
            JAVASCRIPT_FILE,
            "JavaScript",
            ["Munatnt Operator", "Mutant Operator"],
            ["Mutant ID"],
        ),
    ]
    all_rows = pd.concat(frames, ignore_index=True)

    all_rows.drop(
        columns=["operator_set", "unresolved"]
    ).to_csv(OUTPUT_DIR / "cleaning_audit_all_rows.csv", index=False)

    unresolved = all_rows[
        (~all_rows["is_no_operator"]) & (~all_rows["strict_eligible"])
    ].drop(columns=["operator_set", "unresolved"])
    unresolved.to_csv(
        OUTPUT_DIR / "rows_requiring_manual_review.csv", index=False
    )

    strict = all_rows[all_rows["strict_eligible"]].copy()
    strict.to_csv(
        OUTPUT_DIR / "strict_bug_operator_mappings.csv", index=False
    )

    audit_rows = []
    for language, group in all_rows.groupby("language"):
        actual = int(group["strict_eligible"].sum())
        unknown_projects = int((group["project"] == "UnknownProject").sum())
        audit_rows.append({
            "language": language,
            "all_rows": len(group),
            "no_operator_rows": int(group["is_no_operator"].sum()),
            "strict_eligible": actual,
            "expected_in_manuscript": EXPECTED_COUNTS.get(language),
            "matches_expected": actual == EXPECTED_COUNTS.get(language),
            "unique_projects": int(group["project"].nunique()),
            "unknown_project_rows": unknown_projects,
        })

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(OUTPUT_DIR / "dataset_count_audit.csv", index=False)

    project_audit = (
        strict.groupby(["language", "project"], as_index=False)
        .size()
        .rename(columns={"size": "strict_mappings"})
    )
    project_audit.to_csv(
        OUTPUT_DIR / "project_fold_audit.csv", index=False
    )

    print("\nDataset audit:")
    print(audit.to_string(index=False))

    if not audit["matches_expected"].all():
        print(
            "\nWARNING: At least one strict count differs from the manuscript. "
            "Review rows_requiring_manual_review.csv before reporting results."
        )

    if (audit["unknown_project_rows"] > 0).any():
        print(
            "\nWARNING: Some rows have UnknownProject. Review "
            "project_fold_audit.csv before using project-held-out results."
        )

    return strict


# ---------------------------------------------------------------------
# 4. COVERAGE AND PORTFOLIO METHODS
# ---------------------------------------------------------------------

def to_sets(frame: pd.DataFrame) -> List[FrozenSet[str]]:
    return [
        frozenset(text.split(";"))
        for text in frame["operators"]
        if normalize_text(text)
    ]


def complete_fix_coverage(
    operator_sets: Sequence[FrozenSet[str]],
    selected: Iterable[str],
) -> Tuple[int, int, float]:
    selected_set = set(selected)
    covered = sum(required.issubset(selected_set) for required in operator_sets)
    total = len(operator_sets)
    percentage = 100.0 * covered / total if total else np.nan
    return covered, total, percentage


def frequency_ranking(
    operator_sets: Sequence[FrozenSet[str]],
) -> List[str]:
    vocabulary = sorted(set().union(*operator_sets))
    frequency = {
        operator: sum(operator in required for required in operator_sets)
        for operator in vocabulary
    }
    return sorted(vocabulary, key=lambda operator: (-frequency[operator], operator))


def exact_composition_aware_portfolio(
    operator_sets: Sequence[FrozenSet[str]],
    k: int,
) -> Set[str]:
    """
    Exact size-k source-level portfolio maximizing complete-fix coverage.

    Binary variables:
      x_o = 1 when operator o is selected
      y_b = 1 when every operator required by bug b is selected

    Maximize:
      primary objective: number of completely representable fixes
      secondary objective: operator frequency (tie-break only)
    """
    sets = [set(values) for values in operator_sets if values]
    vocabulary = sorted(set().union(*sets))
    number_of_operators = len(vocabulary)
    number_of_bugs = len(sets)

    if number_of_operators == 0:
        return set()

    k = min(k, number_of_operators)
    index = {operator: i for i, operator in enumerate(vocabulary)}

    frequency = np.array([
        sum(operator in required for required in sets)
        for operator in vocabulary
    ], dtype=float)

    # A covered fix dominates every possible frequency tie-break.
    big_m = float(frequency.sum() + 1)

    # scipy.optimize.milp minimizes c^T x.
    objective = np.concatenate([
        -frequency,
        -big_m * np.ones(number_of_bugs),
    ])

    rows: List[np.ndarray] = []
    lower_bounds: List[float] = []
    upper_bounds: List[float] = []

    # Select exactly k operators.
    budget_row = np.zeros(number_of_operators + number_of_bugs)
    budget_row[:number_of_operators] = 1
    rows.append(budget_row)
    lower_bounds.append(k)
    upper_bounds.append(k)

    # y_b <= x_o for every operator required by bug b.
    for bug_index, required in enumerate(sets):
        for operator in required:
            row = np.zeros(number_of_operators + number_of_bugs)
            row[number_of_operators + bug_index] = 1
            row[index[operator]] = -1
            rows.append(row)
            lower_bounds.append(-np.inf)
            upper_bounds.append(0)

    constraints = LinearConstraint(
        csr_matrix(np.vstack(rows)),
        np.array(lower_bounds),
        np.array(upper_bounds),
    )

    result = milp(
        c=objective,
        integrality=np.ones(number_of_operators + number_of_bugs),
        bounds=Bounds(
            np.zeros(number_of_operators + number_of_bugs),
            np.ones(number_of_operators + number_of_bugs),
        ),
        constraints=constraints,
        options={"time_limit": 120},
    )

    if not result.success:
        raise RuntimeError(
            f"MILP failed for k={k}: {result.message}"
        )

    return {
        vocabulary[i]
        for i, value in enumerate(result.x[:number_of_operators])
        if value > 0.5
    }


def random_portfolio_coverage(
    train_sets: Sequence[FrozenSet[str]],
    test_sets: Sequence[FrozenSet[str]],
    k: int,
    rng: np.random.Generator,
) -> Tuple[float, int]:
    vocabulary = sorted(set().union(*train_sets))
    k = min(k, len(vocabulary))

    if k == len(vocabulary):
        covered, total, _ = complete_fix_coverage(test_sets, vocabulary)
        return float(covered), total

    covered_values = []
    for _ in range(N_RANDOM_PORTFOLIOS):
        selected = rng.choice(vocabulary, size=k, replace=False)
        covered, _, _ = complete_fix_coverage(test_sets, selected)
        covered_values.append(covered)

    return float(np.mean(covered_values)), len(test_sets)


# ---------------------------------------------------------------------
# 5. HELD-OUT, SOURCE-LEVEL WITHIN-LANGUAGE EVALUATION
# ---------------------------------------------------------------------

def within_language_project_cv(strict: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED)
    result_rows = []
    portfolio_rows = []

    for language, language_frame in strict.groupby("language"):
        language_frame = language_frame.reset_index(drop=True)
        project_count = language_frame["project"].nunique()

        if project_count < 2:
            raise ValueError(f"{language}: fewer than two projects")

        splitter = GroupKFold(n_splits=min(N_SPLITS, project_count))

        for fold, (train_indices, test_indices) in enumerate(
            splitter.split(language_frame, groups=language_frame["project"]),
            start=1,
        ):
            train = language_frame.iloc[train_indices]
            test = language_frame.iloc[test_indices]

            train_sets = to_sets(train)
            test_sets = to_sets(test)
            frequency_order = frequency_ranking(train_sets)

            for k in K_VALUES:
                frequency_portfolio = set(frequency_order[:k])
                optimal_portfolio = exact_composition_aware_portfolio(train_sets, k)

                methods = {
                    "Frequency-based mutant operator set": frequency_portfolio,
                    "Composition-aware mutant operator set": optimal_portfolio,
                }

                for method, selected in methods.items():
                    covered, total, percentage = complete_fix_coverage(
                        test_sets, selected
                    )
                    result_rows.append({
                        "language": language,
                        "fold": fold,
                        "method": method,
                        "k": k,
                        "covered": covered,
                        "total": total,
                        "coverage_percent": percentage,
                    })
                    portfolio_rows.append({
                        "setting": "within-language project CV",
                        "source_language": language,
                        "target_language": language,
                        "fold": fold,
                        "method": method,
                        "k": k,
                        "operators": ";".join(sorted(selected)),
                    })

                random_covered, total = random_portfolio_coverage(
                    train_sets, test_sets, k, rng
                )
                result_rows.append({
                    "language": language,
                    "fold": fold,
                    "method": "Random mutant operator set",
                    "k": k,
                    "covered": random_covered,
                    "total": total,
                    "coverage_percent": 100.0 * random_covered / total,
                })

    fold_results = pd.DataFrame(result_rows)

    # Sum held-out covered fixes across project folds.
    aggregate = (
        fold_results
        .groupby(["language", "method", "k"], as_index=False)
        .agg(covered=("covered", "sum"), total=("total", "sum"))
    )
    aggregate["coverage_percent"] = (
        100.0 * aggregate["covered"] / aggregate["total"]
    )

    pd.DataFrame(portfolio_rows).to_csv(
        OUTPUT_DIR / "selected_portfolios_within_language.csv", index=False
    )
    fold_results.to_csv(
        OUTPUT_DIR / "within_language_project_cv_folds.csv", index=False
    )
    aggregate.to_csv(
        OUTPUT_DIR / "within_language_project_cv_summary.csv", index=False
    )

    return fold_results, aggregate


# ---------------------------------------------------------------------
# 6. CROSS-LANGUAGE TRANSFER OF SOURCE-LEVEL PORTFOLIOS
# ---------------------------------------------------------------------

def cross_language_transfer(strict: pd.DataFrame) -> pd.DataFrame:
    by_language = {
        language: to_sets(frame)
        for language, frame in strict.groupby("language")
    }

    rows = []

    for source_language, source_sets in by_language.items():
        frequency_order = frequency_ranking(source_sets)

        for k in K_VALUES:
            portfolios = {
                "Frequency-based mutant operator set": set(frequency_order[:k]),
                "Composition-aware mutant operator set":
                    exact_composition_aware_portfolio(source_sets, k),
            }

            for method, selected in portfolios.items():
                for target_language, target_sets in by_language.items():
                    covered, total, percentage = complete_fix_coverage(
                        target_sets, selected
                    )
                    rows.append({
                        "source_language": source_language,
                        "target_language": target_language,
                        "method": method,
                        "k": k,
                        "operators": ";".join(sorted(selected)),
                        "covered": covered,
                        "total": total,
                        "coverage_percent": percentage,
                    })

    results = pd.DataFrame(rows)
    results.to_csv(OUTPUT_DIR / "cross_language_transfer.csv", index=False)
    return results


# ---------------------------------------------------------------------
# 7. PUBLISHED SOURCE-LEVEL BASELINES
# ---------------------------------------------------------------------

def create_source_baseline_template() -> None:
    if SOURCE_BASELINE_FILE.exists():
        return

    template = pd.DataFrame({
        "baseline": ["REPLACE_WITH_PUBLISHED_METHOD"] * 3,
        "language": ["ALL", "ALL", "ALL"],
        "rank": [1, 2, 3],
        "operator": ["CI", "MCR", "MRV"],
    })
    template.to_csv(SOURCE_BASELINE_FILE, index=False)

    print(
        f"\nCreated {SOURCE_BASELINE_FILE}. Replace the example rows with "
        "the exact operator order reported by each source-level prior method."
    )


def evaluate_source_level_baselines(strict: pd.DataFrame) -> pd.DataFrame:
    create_source_baseline_template()

    baseline_data = pd.read_csv(SOURCE_BASELINE_FILE)
    required_columns = {"baseline", "language", "rank", "operator"}
    if not required_columns.issubset(baseline_data.columns):
        raise ValueError(
            f"{SOURCE_BASELINE_FILE} must contain {sorted(required_columns)}"
        )

    # Do not report the untouched placeholder as a real baseline.
    baseline_data = baseline_data[
        baseline_data["baseline"] != "REPLACE_WITH_PUBLISHED_METHOD"
    ].copy()

    if baseline_data.empty:
        print(
            "\nNo published source-level baseline has been supplied yet. "
            "The template was created, but no baseline result was reported."
        )
        return pd.DataFrame()

    target_sets = {
        language: to_sets(frame)
        for language, frame in strict.groupby("language")
    }

    rows = []
    for (baseline, source_language), group in baseline_data.groupby(
        ["baseline", "language"]
    ):
        order = (
            group.sort_values("rank")["operator"]
            .map(normalize_text)
            .tolist()
        )

        unknown = [operator for operator in order if operator not in CANONICAL_OPERATORS]
        if unknown:
            raise ValueError(
                f"{baseline}: operators not in unified taxonomy: {unknown}"
            )

        targets = (
            target_sets.keys()
            if str(source_language).upper() == "ALL"
            else [source_language]
        )

        for target_language in targets:
            if target_language not in target_sets:
                raise ValueError(
                    f"{baseline}: unknown language {target_language}"
                )

            for k in K_VALUES:
                selected = order[:k]
                covered, total, percentage = complete_fix_coverage(
                    target_sets[target_language], selected
                )
                rows.append({
                    "baseline": baseline,
                    "abstraction_level": "source-level",
                    "target_language": target_language,
                    "k": k,
                    "operators": ";".join(selected),
                    "covered": covered,
                    "total": total,
                    "coverage_percent": percentage,
                })

    results = pd.DataFrame(rows)
    results.to_csv(
        OUTPUT_DIR / "published_source_level_baselines.csv", index=False
    )
    return results


# ---------------------------------------------------------------------
# 8. SUPPLEMENTARY PRAPR COMPARISON
# ---------------------------------------------------------------------

def evaluate_prapr_supplementary(strict: pd.DataFrame) -> pd.DataFrame:
    if not PRAPR_FILE.exists():
        print(
            f"\n{PRAPR_FILE} not found. PraPR is skipped. "
            "This is acceptable because it is supplementary, not the "
            "primary source-level baseline."
        )
        return pd.DataFrame()

    prapr = pd.read_csv(PRAPR_FILE)
    required_columns = {"rank", "operator"}
    if not required_columns.issubset(prapr.columns):
        raise ValueError(f"{PRAPR_FILE} must contain {sorted(required_columns)}")

    order = (
        prapr.sort_values("rank")["operator"]
        .map(normalize_text)
        .tolist()
    )
    unknown = [operator for operator in order if operator not in CANONICAL_OPERATORS]
    if unknown:
        raise ValueError(f"PraPR mapped operators are unknown: {unknown}")

    java_sets = to_sets(strict[strict["language"] == "Java"])
    rows = []

    for k in K_VALUES:
        selected = order[:k]
        covered, total, percentage = complete_fix_coverage(
            java_sets, selected
        )
        rows.append({
            "baseline": "PraPR published ranking after label mapping",
            "abstraction_level": "JVM bytecode (supplementary)",
            "target_language": "Java",
            "k": k,
            "operators": ";".join(selected),
            "covered": covered,
            "total": total,
            "coverage_percent": percentage,
        })

    results = pd.DataFrame(rows)
    results.to_csv(
        OUTPUT_DIR / "prapr_supplementary_comparison.csv", index=False
    )
    return results


# ---------------------------------------------------------------------
# 9. MAIN
# ---------------------------------------------------------------------

def main() -> None:
    strict = load_all_data()

    _, within_summary = within_language_project_cv(strict)
    cross_results = cross_language_transfer(strict)
    source_baselines = evaluate_source_level_baselines(strict)
    prapr_results = evaluate_prapr_supplementary(strict)

    print("\nHeld-out within-language results:")
    print(
        within_summary.sort_values(["language", "k", "method"])
        .to_string(index=False)
    )

    print("\nCross-language results saved to:")
    print(OUTPUT_DIR / "cross_language_transfer.csv")

    if not source_baselines.empty:
        print("\nPublished source-level baseline results saved to:")
        print(OUTPUT_DIR / "published_source_level_baselines.csv")

    if not prapr_results.empty:
        print("\nSupplementary PraPR results saved to:")
        print(OUTPUT_DIR / "prapr_supplementary_comparison.csv")

    print(
        "\nInterpretation rule: report these values as complete-fix "
        "representability under a source-level operator-family budget. "
        "Do not describe them as actual repaired bugs unless an APR system "
        "was run and validated separately."
    )


if __name__ == "__main__":
    main()