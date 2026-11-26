## Cli-3 — TypeHandler numeric parsing

**Source file:** `src/java/org/apache/commons/cli/TypeHandler.java`

**Buggy → fixed change:** The buggy version delegates parsing to `NumberUtils.createNumber(str)`. The fixed version explicitly checks that `str` is non-null, distinguishes decimal values using `str.indexOf('.') != -1`, and calls `Double.valueOf(str)` or `Long.valueOf(str)` accordingly.

### Atomic decomposition

| Atomic edit | Patch evidence | Canonical family | Rationale |
|---|---|---|---|
| 1 | `NumberUtils.createNumber(str)` is replaced by explicit numeric parsing calls (`Double.valueOf` / `Long.valueOf`) | **MCR** — Method Call Replacement / Removal | The fix replaces one parsing method call with alternative method calls selected by the input form. |
| 2 | Adds `str != null` and `str.indexOf('.') != -1` conditions | **CI** — Condition Insertion / Removal | The fix introduces explicit conditions to guard null input and select the numeric parsing path. |

**Recorded source annotation:** `MCR[2], CI[36]`.

**Manual-mapping note:** The patch contains both a method-call replacement and newly introduced conditional logic. Keep both families; do not classify the entire hunk under only one label.
