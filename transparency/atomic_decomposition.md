# Atomic Decomposition of Bugs

This file provides atomic transformations for selected bugs using a unified dataset taxonomy.

---

## Taxonomy

- Statement insertion  
- Statement deletion  
- Modification return value  
- Modification of the condition 
- API call replacement / refinement  
- Expression modification  
- Argument replacement / relocation  
- Control-flow statement mutant  
- Early return insertion / deletion  
- Condition insertion / removal  
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
CLI-34 (Commons CLI)
Patch
- private Class type = String.class;
+ private Class type;
- type = String.class;
+ type = null;
Atomic Decomposition
InitializerRemoval(= String.class)
ConstantReplacement(String.class → null)
StatementReplacement(type = String.class → type = null)
Classification
Primary: Constant replacement, Null/default initialization change
Secondary: Statement replacement, Initializer removal
Closure-1 (Closure Compiler)
Patch
- if (!removeGlobals) {
-   return;
- }
Atomic Decomposition
StatementDeletion(if-block)
GuardRemoval(!removeGlobals)
EarlyReturnDeletion(return)
Classification
Primary: Statement deletion
Secondary: Guard removal, Early return deletion
Closure-11 (Closure Compiler)
Patch
+ else if (n.getJSType() != null && parent.isAssign()) {
+   return;
+ }
Atomic Decomposition
ConditionalRefinement(add else-if branch)
StatementInsertion(return)
EarlyReturnInsertion
ControlFlowRestructuring
Classification
Primary: Conditional refinement, Statement insertion
Secondary: Early return insertion, Control-flow restructuring
Closure-122 (Closure Compiler)
Patch
- Pattern p = Pattern.compile(...);
- if (p.matcher(...).find())
+ if (comment.getValue().indexOf("/* @") != -1 || comment.getValue().indexOf("\n * @") != -1)
Atomic Decomposition
StatementDeletion(regex creation)
APICallReplacement(regex → indexOf)
ConditionalReplacement
ExpressionExpansion(A → A || B)
ConstantInsertion(string patterns)
Classification
Primary: API call replacement, Statement deletion
Secondary: Conditional refinement, Expression expansion
Codec-2 (Commons Codec)
Patch
- if (lineLength > 0 && pos > 0)
+ if (lineLength > 0)
Atomic Decomposition
ConditionalRefinement
SubconditionDeletion(pos > 0)
ExpressionSimplification
Classification
Primary: Conditional refinement
Secondary: Subcondition deletion
Codec-7 (Commons Codec)
Patch
- encodeBase64(binaryData, false)
+ encodeBase64(binaryData, true)
Atomic Decomposition
ArgumentReplacement(false → true)
ConstantReplacement
APICallRefinement
Classification
Primary: Argument replacement, Constant replacement
Secondary: API refinement
Gson-15 (Gson)
Patch
- if (!lenient && (Double.isNaN(value) || Double.isInfinite(value)))
+ if (Double.isNaN(value) || Double.isInfinite(value))
Atomic Decomposition
ConditionalRefinement
GuardRemoval(!lenient)
SubconditionDeletion
ExpressionSimplification
Classification
Primary: Conditional refinement
Secondary: Guard removal, Expression simplification
