## Cli-8 — HelpFormatter wrapping position

**Source file:** `src/java/org/apache/commons/cli/HelpFormatter.java`

**Buggy → fixed change:** The buggy version passes `nextLineTabStop` as the third argument to `findWrapPos`. The fixed version passes the literal constant `0`.

### Atomic decomposition

| Atomic edit | Patch evidence | Canonical family | Rationale |
|---|---|---|---|
| 1 | Replaces `nextLineTabStop` with `0` in the `findWrapPos` call | **CR** — Constant Replacement | The argument expression is changed to the literal constant `0`, matching the source annotation's constant-replacement family. |

**Recorded source annotation:** `CR[6]`.

**Manual-mapping note:** This is one atomic argument replacement. Do not split the method invocation and its argument change into separate operators.
