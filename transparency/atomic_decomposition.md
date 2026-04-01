# Atomic Decomposition of Bugs

This file provides atomic transformations for selected bugs using a unified dataset taxonomy.

---

## Example: Extracting Patch for a Defects4J Bug

### Step 1: Checkout Buggy Version
```bash
defects4j checkout -p Cli -v 2b -w Cli_2_buggy


Step 2: Checkout Fixed Version
defects4j checkout -p Cli -v 2f -w Cli_2_fixed


Step 3: Generate Patch (Diff)
git diff --no-index Cli_2_buggy Cli_2_fixed > Cli_2.patch


Output

The file Cli_2.patch contains the full patch (difference between buggy and fixed versions).



Notes
b = buggy version
f = fixed version
Works for all Defects4J projects by changing project name and bug ID


## Taxonomy

## Taxonomy (Aligned with Mutant Operators)

- CI  : Condition Insertion / Removal  
- MCR : Method Call Replacement / Removal  
- MRV : Modification of Return Value  
- LOR : Logical Operator Replacement  
- VA  : Variable Assignment / Removal  
- ROR : Relational Operator Replacement  
- MPM : Method Parameter Modification  
- MOCS: Modification of Condition Statement  
- DOC : Condition Deletion / Insertion  
- SD  : Statement Deletion / Insertion  
- MA  : Method Addition / Removal  
- AIS : Import Statement Addition / Deletion  
- DTR : Data Type Replacement  
- CR  : Constant Replacement  
- SR  : Statement Reordering  
- EII : Else-If Insertion  
- VR  : Variable Replacement  
- CFSM: Control Flow Mutation  
- SI  : Statement Insertion  
- BCO : Boundary Condition Operator  
- EI  : Exception Insertion  
- FLI : For Loop Insertion  
- WLI : While Loop Insertion  
- CASEI: Case Insertion  
- AA  : Annotation Addition  
- SM  : String Modification  
- ElseI: Else Insertion  
- BR  : Bracket Reordering  
- AOR : Arithmetic Operator Replacement  
- DIS : Import Statement Deletion  
- BWO : Bitwise Operator Replacement  
- RAR : Reference Assignment Replacement  
- CN  : Condition Negation  

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
- private Class type = String.class;
+ private Class type;
- type = String.class;
+ type = null;


Atomic Decomposition
VA (Variable Assignment → String.class → null)
DTR (Data Type Replacement → implicit default instead of explicit type)
CR (Constant Replacement → String.class → null)
Classification
Primary: VA, DTR
Secondary: CR


Gson-15 (Gson)
Patch
- if (!lenient && (Double.isNaN(value) || Double.isInfinite(value))) {
+ if (Double.isNaN(value) || Double.isInfinite(value)) {



Atomic Decomposition
DOC (Deletion of Condition → !lenient removed)
MOCS (Modification of Conditional Statement)
LOR (Logical Operator Replacement → removal of && dependency)
Classification
Primary: DOC, MOCS
Secondary: LOR


Gson-10 (Gson)
Patch
- TypeAdapter t = jsonAdapterPresent ? typeAdapter
-     : new TypeAdapterRuntimeTypeWrapper(context, typeAdapter, fieldType.getType());
+ TypeAdapter t =
+     new TypeAdapterRuntimeTypeWrapper(context, typeAdapter, fieldType.getType());


Atomic Decomposition
DOC (Deletion of conditional expression)
MOCS (Modification of Conditional Statement → ternary removed)
MCR (Method Call Replacement → enforced wrapper usage)
Classification
Primary: MCR
Secondary: DOC, MOCS


CSV-1 (Commons CSV)
Patch
- if (current == '\r' || (current == '\n' && lastChar != '\r')) {
+ if (current == '\n') {


Atomic Decomposition
MOCS (Modification of Conditional Statement)
LOR (Logical Operator Replacement → OR condition removed)
DOC (Deletion of condition parts → '\r' and lastChar dependency)
Classification
Primary: MOCS
Secondary: LOR, DOC

## JacksonXML-3 (Jackson XML)

### Patch
```diff
case XmlTokenStream.XML_ATTRIBUTE_VALUE:
+ _currText = _xmlTokens.getText();
  _currToken = JsonToken.VALUE_STRING;
- return (_currText = _xmlTokens.getText());
+ break;



Atomic Decomposition
SD (Statement Deletion → removal of return statement)
SI (Statement Insertion → assignment moved before token setting)
CFSM (Control Flow Mutation → return → break)
VA (Variable Assignment → explicit assignment separated from return)


## JacksonDatabind-101 (Jackson Databind)

### Patch
```diff
while (t == JsonToken.FIELD_NAME) {
    // NOTE: do NOT skip name as it needs to be copied; `copyCurrentStructure` does that
+   p.nextToken();
    tokens.copyCurrentStructure(p);
    t = p.nextToken();
}
...
- if (t != JsonToken.END_OBJECT) {
-     ctxt.reportWrongTokenException(this, JsonToken.END_OBJECT, 
-             "Attempted to unwrap '%s' value",
-             handledType().getName());
- }
tokens.writeEndObject();



Atomic Decomposition
SI (Statement Insertion → p.nextToken();)
SD (Statement Deletion → removal of sanity-check if block)
DOC (Condition Deletion / Insertion → deletion of if (t != JsonToken.END_OBJECT))
MCR (Method Call Replacement / Removal → removal of ctxt.reportWrongTokenException(...))
CFSM (Control Flow Mutation → exception path removed, normal flow continues)


## JacksonCore-14 (Jackson Core)

### Patch
```diff
- if ((toRelease != src) && (toRelease.length < src.length)) { throw wrongBuf(); }
+ if ((toRelease != src) && (toRelease.length <= src.length)) { throw wrongBuf(); }
- return new IllegalArgumentException("Trying to release buffer smaller than original");
+ return new IllegalArgumentException("Trying to release buffer not owned by the context");



Atomic Decomposition
ROR (Relational Operator Replacement → < → <=)
MOCS (Modification of Condition Statement → boundary condition updated)
SM (String Modification → error message changed)
Classification
Primary: ROR
Secondary: MOCS, SM

