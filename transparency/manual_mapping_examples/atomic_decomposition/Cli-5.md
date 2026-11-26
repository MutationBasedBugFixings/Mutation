## Cli-5 — Null handling in stripLeadingHyphens

**Source file:** `src/java/org/apache/commons/cli/Util.java`

**Buggy → fixed change:** The fixed version adds an explicit null guard at the beginning of `stripLeadingHyphens(String str)`. If `str` is null, the method returns null before calling `startsWith`.

### Atomic decomposition

| Atomic edit | Patch evidence | Canonical family | Rationale |
|---|---|---|---|
| 1 | Inserts `if (str == null)` | **CI** — Condition Insertion / Removal | A new guard condition is added to handle null input. |
| 2 | Inserts `return null` inside the guard | **MRV** — Modification of Return Value | The method now explicitly returns null for this input case instead of proceeding to dereference it. |

**Recorded source annotation:** `CI[36], MRV[145]`.

**Manual-mapping note:** These are two related but distinguishable parts of the fix: the guard condition and the return behavior. Retain both labels as recorded.
