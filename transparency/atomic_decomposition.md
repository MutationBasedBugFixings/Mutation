# Atomic Decomposition of Bugs

This file provides atomic transformations for selected bugs using a unified dataset taxonomy.

---

## Taxonomy

- Statement insertion  
- Statement deletion  
- Statement replacement  
- Conditional refinement  
- API call replacement / refinement  
- Expression modification  
- Argument replacement / relocation  
- Control-flow restructuring  
- Early return insertion / deletion  
- Guard insertion / removal  
- Constant replacement  
- Null/default initialization change  

---

## CLI-2 (Commons CLI)

### Patch
```diff
- tokens.add(token);
- break;
+ tokens.add("-" + ch);

Atomic Decomposition
StatementReplacement(tokens.add(token) → tokens.add("-" + ch))
ExpressionModification(token → "-" + ch)
StatementDeletion(break)
Classification
Primary: Statement replacement, Statement deletion
Secondary: Expression modification, Loop-control modification
