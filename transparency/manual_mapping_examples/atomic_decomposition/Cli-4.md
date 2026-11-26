## Cli-4 — Missing required option message

**Source file:** `src/java/org/apache/commons/cli/Parser.java`

**Buggy → fixed change:** The buggy version creates an empty `StringBuffer`. The fixed version initializes it with `"Missing required option"`, appends a plural suffix when more than one option is missing, and appends `": "` before listing the options.

### Atomic decomposition

| Atomic edit | Patch evidence | Canonical family | Rationale |
|---|---|---|---|
| 1 | Replaces `new StringBuffer()` with a buffer initialized with the message prefix, then appends the plural suffix and separator | **SM** — String Modification | The semantic change reconstructs the missing-option message and its formatting. The ternary expression is part of pluralizing the message; it is not separately counted as a standalone control-flow repair in this annotation. |

**Recorded source annotation:** `SM[30]`.

**Manual-mapping note:** Treat the message construction as one cohesive string-formatting repair. Do not count each appended string fragment as a separate operator.
