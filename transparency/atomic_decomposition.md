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



### Patchs 

## CLI-2 (Commons CLI)
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


## CLI-34 (Commons CLI)

### Patch
```diff
diff --git a/src/main/java/org/apache/commons/cli/Option.java b/src/main/java/org/apache/commons/cli/Option.java
@@
- private Class type = String.class;
+ private Class type;


diff --git a/src/main/java/org/apache/commons/cli/OptionBuilder.java b/src/main/java/org/apache/commons/cli/OptionBuilder.java
@@
- type = String.class;
+ type = null;

Atomic Decomposition
InitializerRemoval(= String.class)
ConstantReplacement(String.class → null)
StatementReplacement(type = String.class → type = null)
Classification
Primary: Constant replacement, Null/default initialization change
Secondary: Statement replacement, Initializer removal


## Gson-15 (Gson)

### Patch
```diff
diff --git a/gson/src/main/java/com/google/gson/stream/JsonWriter.java b/gson/src/main/java/com/google/gson/stream/JsonWriter.java
@@
- if (!lenient && (Double.isNaN(value) || Double.isInfinite(value))) {
+ if (Double.isNaN(value) || Double.isInfinite(value)) {


Atomic Decomposition
ConditionalRefinement
GuardRemoval(!lenient)
SubconditionDeletion(!lenient &&)
ExpressionSimplification
Classification
Primary: Conditional refinement
Secondary: Guard removal, Expression simplification


## Gson-10 (Gson)

### Patch
```diff
diff --git a/gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java b/gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java
@@
- TypeAdapter t = jsonAdapterPresent ? typeAdapter
-     : new TypeAdapterRuntimeTypeWrapper(context, typeAdapter, fieldType.getType());
+ TypeAdapter t =
+     new TypeAdapterRuntimeTypeWrapper(context, typeAdapter, fieldType.getType());


Atomic Decomposition
ConditionalRemoval(jsonAdapterPresent ? ... : ...)
StatementReplacement(conditional assignment → direct assignment)
APICallNormalization(always use TypeAdapterRuntimeTypeWrapper)
Classification
Primary: Statement replacement
Secondary: Conditional removal, API call refinement



## CSV-1 (Commons CSV)

### Patch
```diff
diff --git a/src/main/java/org/apache/commons/csv/ExtendedBufferedReader.java b/src/main/java/org/apache/commons/csv/ExtendedBufferedReader.java
@@
- if (current == '\r' || (current == '\n' && lastChar != '\r')) {
+ if (current == '\n') {


Atomic Decomposition
ConditionalRefinement
SubconditionDeletion(current == '\r')
SubconditionDeletion((current == '\n' && lastChar != '\r') → simplified)
ExpressionSimplification
Classification
Primary: Conditional refinement
Secondary: Subcondition deletion, Expression simplification
