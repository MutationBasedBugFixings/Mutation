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

