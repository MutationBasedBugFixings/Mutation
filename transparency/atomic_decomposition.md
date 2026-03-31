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
