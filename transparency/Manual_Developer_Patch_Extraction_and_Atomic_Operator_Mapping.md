# Manual Developer-Patch Extraction and Atomic Operator Mapping

## Purpose

This document describes the **manual mapping workflow** used to inspect original developer fixes, extract their patches, and decompose those patches into atomic repair operations before assigning the study's canonical mutant-operator taxonomy.

This is a source-annotation and manual-mapping procedure. It is **not an RQ5 experiment or an RQ5 result-generation procedure**.

The worked example is **Defects4J Cli-1**. The same procedure applies to another active Defects4J project/bug by changing the project identifier and bug number.

---

## 1. Set up Defects4J

On the research server, activate the environment in which Defects4J is installed and add its executable directory to `PATH`:

```bash
export PATH="/home1/furqan/tools_and_libs/defects4j/framework/bin:$PATH"

which defects4j
defects4j info -p Cli -b 1
```

The `info` command verifies that the project and bug identifier are recognised by the installed Defects4J version.

## 2. Checkout the buggy version

Create a working directory and checkout the buggy version:

```bash
mkdir -p "$HOME/manual_mapping/defects4j/checkouts"

defects4j checkout \
    -p Cli \
    -v 1b \
    -w "$HOME/manual_mapping/defects4j/checkouts/Cli-1"
```

Meaning:

- `-p Cli`: Defects4J project identifier.
- `-v 1b`: bug 1, buggy version (`b`).
- `-w`: checkout working directory.

**Important:** Perform this as one checkout. Defects4J initializes a local Git repository in this working directory and creates local tags for both the buggy and fixed program versions of the selected bug.

## 3. Enter the checkout and inspect the version tags

```bash
cd "$HOME/manual_mapping/defects4j/checkouts/Cli-1"

git tag --list 'D4J_Cli_1_*'
```

The expected relevant tags are:

```text
D4J_Cli_1_BUGGY_VERSION
D4J_Cli_1_FIXED_VERSION
```

The exact tag names are generated from the project identifier and bug ID.

## 4. Obtain the buggy and fixed commit hashes

This is the command sequence used to obtain the two revision identifiers:

```bash
echo "BUGGY VERSION:"
git rev-parse D4J_Cli_1_BUGGY_VERSION

echo "FIXED VERSION:"
git rev-parse D4J_Cli_1_FIXED_VERSION
```

For reuse in the next command, save the hashes in shell variables:

```bash
BUGGY=$(git rev-parse 'D4J_Cli_1_BUGGY_VERSION^{commit}')
FIXED=$(git rev-parse 'D4J_Cli_1_FIXED_VERSION^{commit}')

echo "Buggy commit: $BUGGY"
echo "Fixed commit: $FIXED"
```

The `^{commit}` suffix makes Git resolve the tag to its commit object.

## 5. Extract the original developer patch using `git diff`

This is the key command. It compares the buggy revision first and the fixed revision second. The resulting patch therefore shows the developer's changes from buggy code to fixed code.

```bash
mkdir -p "$HOME/manual_mapping/defects4j/patches"

git diff \
    --no-ext-diff \
    --binary \
    --unified=80 \
    "$BUGGY" \
    "$FIXED" \
    > "$HOME/manual_mapping/defects4j/patches/Cli-1.patch"
```

The original developer patch is now saved as:

```text
~/manual_mapping/defects4j/patches/Cli-1.patch
```

Check that the patch was created and is not empty:

```bash
ls -lh "$HOME/manual_mapping/defects4j/patches/Cli-1.patch"

test -s "$HOME/manual_mapping/defects4j/patches/Cli-1.patch" \
    && echo "Developer patch extracted successfully"
```

## 6. Inspect the changed files and patch

List the files changed between the buggy and fixed versions:

```bash
git diff --name-status "$BUGGY" "$FIXED"
```

Show the change summary:

```bash
git diff --stat "$BUGGY" "$FIXED"
```

Open the full developer patch:

```bash
less "$HOME/manual_mapping/defects4j/patches/Cli-1.patch"
```

Or print it to the terminal:

```bash
cat "$HOME/manual_mapping/defects4j/patches/Cli-1.patch"
```

The patch contains the old code (lines beginning with `-`) and the new code (lines beginning with `+`), together with file names and hunk context.

## 7. Save the revision information for manual-mapping traceability

For every mapped bug, retain the exact revision identifiers and changed-file list with the patch:

```bash
OUT="$HOME/manual_mapping/defects4j/patches/Cli-1"

mkdir -p "$OUT"

{
    echo "Benchmark: Defects4J"
    echo "Project: Cli"
    echo "Bug ID: 1"
    echo "Buggy tag: D4J_Cli_1_BUGGY_VERSION"
    echo "Fixed tag: D4J_Cli_1_FIXED_VERSION"
    echo "Buggy commit: $BUGGY"
    echo "Fixed commit: $FIXED"
    echo
    echo "Changed files:"
    git diff --name-status "$BUGGY" "$FIXED"
    echo
    echo "Change summary:"
    git diff --stat "$BUGGY" "$FIXED"
} > "$OUT/metadata.txt"

cp "$HOME/manual_mapping/defects4j/patches/Cli-1.patch" \
   "$OUT/Cli-1.patch"
```

A per-bug record should retain:

```text
Cli-1/
├── Cli-1.patch
└── metadata.txt
```

---

## 8. Reusable command for any Defects4J project and bug

After confirming the Cli-1 example works, define this function once in the terminal. It performs the checkout, retrieves the buggy/fixed hashes, extracts the patch, and writes metadata.

```bash
extract_manual_patch() {
    PROJECT="$1"
    BUG="$2"

    ROOT="$HOME/manual_mapping/defects4j"
    WORK="$ROOT/checkouts/${PROJECT}-${BUG}"
    OUT="$ROOT/patches/${PROJECT}-${BUG}"

    mkdir -p "$ROOT/checkouts" "$OUT"

    echo "Checking Defects4J bug: ${PROJECT}-${BUG}"

    defects4j info -p "$PROJECT" -b "$BUG" || return 1

    # Checkout the buggy version. Defects4J creates both version tags.
    defects4j checkout \
        -p "$PROJECT" \
        -v "${BUG}b" \
        -w "$WORK" || return 1

    cd "$WORK" || return 1

    BUGGY_TAG="D4J_${PROJECT}_${BUG}_BUGGY_VERSION"
    FIXED_TAG="D4J_${PROJECT}_${BUG}_FIXED_VERSION"

    # Confirm that both tags exist.
    git show-ref --verify --quiet "refs/tags/$BUGGY_TAG" || {
        echo "ERROR: Buggy tag not found: $BUGGY_TAG"
        return 1
    }

    git show-ref --verify --quiet "refs/tags/$FIXED_TAG" || {
        echo "ERROR: Fixed tag not found: $FIXED_TAG"
        return 1
    }

    BUGGY=$(git rev-parse "${BUGGY_TAG}^{commit}") || return 1
    FIXED=$(git rev-parse "${FIXED_TAG}^{commit}") || return 1

    echo "Buggy commit: $BUGGY"
    echo "Fixed commit: $FIXED"

    # Extract the original developer patch: buggy -> fixed.
    git diff \
        --no-ext-diff \
        --binary \
        --unified=80 \
        "$BUGGY" "$FIXED" \
        > "$OUT/${PROJECT}-${BUG}.patch" || return 1

    test -s "$OUT/${PROJECT}-${BUG}.patch" || {
        echo "ERROR: Patch is empty; inspect the tags and revisions."
        return 1
    }

    {
        echo "Benchmark: Defects4J"
        echo "Project: $PROJECT"
        echo "Bug ID: $BUG"
        echo "Buggy tag: $BUGGY_TAG"
        echo "Fixed tag: $FIXED_TAG"
        echo "Buggy commit: $BUGGY"
        echo "Fixed commit: $FIXED"
        echo
        echo "Changed files:"
        git diff --name-status "$BUGGY" "$FIXED"
        echo
        echo "Change summary:"
        git diff --stat "$BUGGY" "$FIXED"
    } > "$OUT/metadata.txt"

    echo "Patch: $OUT/${PROJECT}-${BUG}.patch"
    echo "Metadata: $OUT/metadata.txt"
}
```

Example usage:

```bash
extract_manual_patch Cli 1
extract_manual_patch Chart 3
extract_manual_patch Jsoup 17
```

Run one bug at a time initially and inspect its patch. If a bug is deprecated or unavailable in the installed Defects4J version, record that status rather than substituting a different bug.

---

## 9. Manual atomic decomposition of the developer patch

Once the original patch has been extracted, use the patch as the evidence for manual operator mapping.

### 9.1 Read the complete patch

```bash
less "$HOME/manual_mapping/defects4j/patches/Cli-1.patch"
```

Inspect:

- Which production source files changed.
- Which methods or constructors were modified.
- Which statements, expressions, variables, conditions, or method calls changed.
- Whether the patch contains multiple independent changes.
- Whether any hunks only add or modify tests.

### 9.2 Separate production-code changes from test changes

Keep the entire original developer patch unchanged for traceability. For operator mapping, distinguish:

- Production-code changes: candidates for repair-operator classification.
- Test-only changes: retain as part of the original patch, but do not count as production repair operators.

Do not silently discard a patch hunk. Record why a hunk is excluded from operator classification.

### 9.3 Decompose the production fix into atomic operations

An atomic operation is the smallest independently identifiable semantic edit that can be assigned to the study's taxonomy.

For example, if a developer patch:

1. Replaces an existing method call.
2. Inserts a new condition.
3. Changes a variable assignment.

These are potentially three separate atomic operations, provided each change is independently supported by the patch and the taxonomy.

Do not split one semantic edit into multiple operators merely because several tokens or lines changed. Conversely, do not force multiple independent edits into a single operator.

### 9.4 Assign the canonical taxonomy labels

Use the exact operator names and abbreviations already established in the study's taxonomy. Do not invent a new label, rename a family, or merge two families solely to reconcile frequency totals.

If a patch contains multiple operator families, record all supported families. If a change cannot be confidently classified, mark it for manual adjudication rather than guessing.

### 9.5 Record the annotation evidence

Use a manual-mapping record with these fields:

| Field | What to record |
|---|---|
| Project | Defects4J project ID |
| Bug ID | Original bug identifier |
| Buggy commit | Exact buggy hash |
| Fixed commit | Exact fixed hash |
| Patch file | Path to original `.patch` |
| Changed source file | Production file containing the fix |
| Method | Method/constructor affected, if identifiable |
| Old code | Relevant buggy code |
| New code | Corresponding fixed code |
| Atomic operation | Minimal semantic edit |
| Operator family | Exact canonical taxonomy label |
| Rationale | Evidence supporting the classification |
| Test-only change | Whether the hunk is test-only |
| Review status | Confirmed / Needs review / Unresolved |

The patch is the original evidence artifact. The atomic-mapping record is the manual annotation derived from it. Keep both linked by project and bug ID.

---



## 10. Reproducibility checks

For each mapped bug, verify the following:

1. The Defects4J checkout completed successfully.
2. Both `BUGGY_VERSION` and `FIXED_VERSION` tags exist.
3. The buggy and fixed hashes are recorded.
4. The patch was generated in the correct direction: buggy first, fixed second.
5. The patch is non-empty, unless the case is explicitly documented as an exception.
6. Changed production files are identified separately from test files.
7. Every assigned operator family is supported by an identifiable atomic edit.
8. The manual mapping record links back to the original patch and commit hashes.

**Do not use an empty patch, missing tag, failed checkout, or unavailable bug as evidence for an operator classification. Record it as an extraction failure or unresolved case.**

## References

- Defects4J repository and official README: https://github.com/rjust/defects4j
- Defects4J checkout command: https://defects4j.org/html_doc/d4j/d4j-checkout.html
- Defects4J project checkout implementation: https://github.com/rjust/defects4j/blob/master/framework/core/Project.pm
- Defects4J tag-prefix implementation: https://github.com/rjust/defects4j/blob/master/framework/core/Utils.pm

The Defects4J implementation creates a local Git repository and tags both the buggy and fixed program revisions when checking out a bug. The generated tags follow the form `D4J_<Project>_<Bug>_BUGGY_VERSION` and `D4J_<Project>_<Bug>_FIXED_VERSION`.
