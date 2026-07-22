# Phase 5 successor proposal

Status: NON-AUTHORITATIVE REVIEW MATERIAL, 2026-07-21. This document, its
generator, and its generated candidate do not amend the numbered
specification, protected conformance material, architecture, roadmap, resource
profile, compiler, or release authority. Exact v0.9 remains active until the
owner approves exact successor bytes and the repository's guarded version-bump
procedure completes.

This proposal consults the approved compiler architecture, especially frontend
Decision 6, semantic Decision 7, systems Decision 15, `THE-PLAN.md` Phase 5,
and exact v0.9 GRAM-2 through GRAM-5, TYPE-6, OP-1, FN-1, FN-4, FN-7, PRE-1,
PROG-2, and DIAG-1.

## Result of hostile review

The entrance packet's combined nominal/constructor namespace cannot be the
successor rule. Every source `struct S` declares both a nominal type `S` and a
constructor `S`. PRE-1 also deliberately contains the enum/variant pairs
`Overflow`/`Overflow` and `NarrowError`/`NarrowError`. A combined namespace
would reject every struct and the active prelude itself.

The corrected proposal has three grammar-selected TYPEID domains:

1. nominal types;
2. constructors; and
3. contracts.

A struct declaration enters the first two with one declaration event. The two
entries do not collide with each other. Constructors remain globally unique
and context-free within the constructor domain.

## Exact candidate blocks

The generator extracts only the four blocks delimited below. The delimiters
are not emitted into the candidate.

<!-- CANDIDATE:HEADER:BEGIN -->
# Kernel Specification v0.10

Status: REVIEW CANDIDATE v0.10 (2026-07-21; Phase-5 resolver entrance proposal). Proposes three grammar-selected TYPEID lookup domains, table-derived operation-name reservation, and deterministic declaration-inventory and lexical-resolution diagnostics. These bytes are non-authoritative review material until their complete evidence, protected-surface delta, full-document hash, exact owner approval, guarded baseline update, and active-target installation complete.

Prior: DRAFT v0.9 (2026-07-21; canonical-frontend entrance closure). Defines one executable tree-derived source format, a total host-independent finite-float spelling, exact raw-lexical and pre-tree diagnostic locations, ordered logical-source compilation-unit formation, and a deterministic terminal-predicate and strong-LL(2) grammar contract. The grammar excludes exact fixed lowercase terminals from IDENT, factors ordinary-let, try-let, value-match, and statement-match decisions, gives the two match positions distinct node kinds, admits literal law arguments, and parses semantic law-name and `requires` subsets as ordinary syntax before checking them. Source-law admission is fixed to one closed compiler-independent integer-table discharge rather than optional prover strength. This version also makes every top-level function signature visible throughout the closed compilation unit while retaining declaration-before-use for all other declarations, fixes the FORM-4 grammar reference, and assigns `requires` reservation rejection to FORM-3. These exact bytes are authoritative only after their complete evidence, protected-surface delta, and full-document hash receive advance owner approval and the bytes are installed through the guarded version-bump procedure.
<!-- CANDIDATE:HEADER:END -->

### TYPE-6 replacement

<!-- CANDIDATE:TYPE_6:BEGIN -->
[TYPE-6] Name resolution uses the following closed declaration domains. The grammar role, never an inferred type or expected result, selects the domain and admissible declaration class.

| domain | declarations | admitted uses |
|---|---|---|
| lexical IDENT | top-level `fn_decl`; top-level `const_decl`; const `gparam`; `param`; `let_stmt`; second IDENT of `fieldbind` | a `callee` or `fn_bind` right IDENT admits only a top-level function; `const` IDENT admits only an in-scope const generic or earlier named const; `cvalue` IDENT admits only an earlier named const; `pbase` admits only an in-scope value binding or named const |
| nominal-type TYPEID | source `struct_decl` and `enum_decl` names; PRE-1 nominal types; lexical type `gparam`s overlay this domain while live | `type` TYPEID and the TYPEID suffix of a FORM-5 generic numeric literal admit a live type generic where that form requires one, otherwise a nominal type |
| constructor TYPEID | each source struct constructor under its struct TYPEID; every source enum `variant`; PRE-1 variants, classified as struct-constructor or enum-variant | the leading TYPEID of `construct` admits either class; the leading TYPEID of `arm` admits only enum-variant |
| contract TYPEID | source `contract_decl` names and PRE-1 contract names, including `Int` and `Float` | the optional bound TYPEID of a type `gparam` and the contract TYPEID of `conform_decl` |
| REGIONID | `region_params` and `region_stmt` | every REGIONID in `type`, `mode`, `targ`, `effect`, and `borrow_expr` |
| LABEL | `loop_stmt` | `break_stmt` |

A source struct contributes one declaration event that adds one nominal-type entry and one constructor entry with the same spelling. Those entries do not collide because the grammar distinguishes a `type` role from a `construct` or `arm` role. An enum declaration adds only its nominal type; each variant adds its constructor. Entries must be unique within, but not across, the nominal-type, constructor, and contract domains. Constructor uniqueness is whole-unit and context-free, so construction and matching never consult an expected nominal type.

PRE-1 contributes exactly twenty-four declaration records in this preorder: each enum nominal, then its type parameters in list order, then each variant and that variant's fields in list order, followed by the contracts in declaration order. They are six nominal enums, ten enum-variant constructors, three owner-local type parameters (`Option.T`, `Result.T`, and `Result.E`), three owner-table fields, and two contracts. Exactly the six nominals, ten constructors, and two contracts enter the source resolver's whole-unit lookup inventory and are visible throughout the closed unit. The three type parameters resolve only within their owning compiled PRE-1 declaration, the three fields enter only their owning variant table, and none of those six owner-local records is visible to source lookup. PRE-1 records have no source event or source node. Every top-level function signature is visible throughout the closed compilation unit after unit formation and before any semantic use is resolved [FN-1]. A source nominal type or contract becomes visible immediately after its declaring TYPEID terminal. A source struct constructor becomes visible at that same terminal; an enum-variant constructor becomes visible immediately after its variant TYPEID terminal. Each remains visible through the end of the unit. Whole-unit inventory checks uniqueness but grants no earlier visibility; a use before one of these declaration points is rejected even though inventory knows the later declaration exists.

A generic TYPEID parameter becomes visible after its declaring terminal through the remainder of its declaration's generic, header, and body scope. It may not redeclare another parameter in the same generic list or shadow a live nominal type or enclosing generic type. Constructor and contract spellings are separate grammar-selected domains and do not participate in that comparison. A const generic becomes visible after its complete `gparam`. A region parameter becomes visible after its terminal through the remainder of its signature and body; for `fn_sig`, that scope ends at the signature terminator. Independently of visibility, OWN-3 requires every REGIONID declaration to be unique throughout its owning function declaration or contract-member signature, parameters included: a later region parameter or local region may not reuse an earlier region spelling even after the earlier region's lexical scope has ended. A `fn_decl` parameter becomes visible after its complete `param` through the function's requires block and body. A `fn_sig` parameter becomes visible after its complete `param` through that signature's terminator; duplicate parameters in that signature are same-scope redeclarations even though v0.10 has no lexical value-use role in the remaining suffix. A `let_stmt` binder becomes visible only after its complete initializer statement through the end of its lexical block; a requires-block let is visible only to later requires entries and not to the function body [FN-8]. A match binder becomes visible in its arm body only after the complete fieldbind list and only after GRAM-10 has established that it differs from its paired field label, every earlier binder in that arm list, and every lexical-IDENT declaration live on arm entry. A loop label and local region are visible only in their respective bodies. A named const becomes visible only after its complete `const_decl`, preserving CONST-2's explicitly-earlier rule.

Within one domain, two declarations in the compilation-unit root or in the same lexical scope are a redeclaration attributed to the later declaration event. Declarations in unrelated function or declaration owners are not duplicates merely because their spellings match. A nested lexical declaration may not shadow an entry live at that declaration. OWN-3's function-wide REGIONID uniqueness is stricter than either rule and is reported at the later region declaration with the conflicting region origin. GRAM-10 exclusively owns match-binder distinctness and freshness: a second `fieldbind` IDENT equal to its paired field label, an earlier binder in the same arm list, or any lexical-IDENT declaration live on arm entry is rejected citing GRAM-10 at that later/offending binder before it becomes a declaration, rather than also being reported as TYPE-6 shadowing. Because every top-level function is live throughout the unit, any other parameter, local, or const generic in a nested scope may not use a top-level function spelling even when that function's source item occurs later; the nested declaration is the offending shadow event. Disjoint expired lexical scopes may reuse an ordinary value or label spelling; REGIONID reuse remains forbidden throughout one function by OWN-3. Logical paths and record boundaries never create a namespace, scope, or lookup key [PROG-2].

The owner-dependent declaration and use roles are exactly the carriers classified by [DIAG-1]. They do not enter or query a lexical name domain. DIAG-1 retains each for later typed owner/member checking. Deferral is neither acceptance nor rejection of its later owner/member relation.
<!-- CANDIDATE:TYPE_6:END -->

### OP-1 paragraph replacement

<!-- CANDIDATE:OP_1_NAMES:BEGIN -->
Let `DotlessOperationNames` be exactly the set of distinct individual operation spellings enumerated in this rule's normative `op` column whose complete spelling satisfies IDENT and contains no dot. Let `ModeWords` be exactly the suffix alternatives in FORM-3's active OPNAME formation rule; in this version it equals `{wrap, trap, checked, sat, strict}`. `ReservedLowerNames` is exactly `DotlessOperationNames` union `ModeWords`. A printed review list is non-authoritative and, when present, must equal the corresponding derived set.

Each distinct complete spelling in the operation table declares one operation-family identity, even when more than one row carries that spelling; the two `cvt` rows therefore belong to one `cvt` family. An OPNAME callee resolves to its exactly spelled operation family. An IDENT callee whose spelling belongs to `DotlessOperationNames` resolves to that operation family; every other IDENT callee admits only a top-level source `fn_decl`. Absence from the selected operation-family or function inventory is a hard error citing OP-1. Later typed operation checking uses the written type arguments and operand domains to select the applicable row within the resolved family. Operand types never select between an operation family and a function.

No source declaration in this closed list may use a member of `ReservedLowerNames`: the IDENT of `fn_decl`; the IDENT of `const_decl`; every `param` IDENT; every `let_stmt` IDENT, including ordinary, try, value-match, and requires-block lets; the second IDENT of `fieldbind`; every `field` and `vfield` IDENT; and the IDENT-shaped interior of `region_params` and `region_stmt`. Such a reserved binding is rejected citing exactly FORM-3. Dependent field declarations participate in this pre-resolution reservation inventory even though their owner/member duplicates remain deferred. No other declaration role is covered: type-generic TYPEIDs, const-generic IDENTs, LABELs, and contract-member `fn_sig` IDENTs remain outside this prohibition. Dotted OPNAMEs cannot be declarations under the grammar. This reservation keeps operation-versus-function resolution context-free [META-2] and keeps a field-access place from maximal-munching as OPNAME [FORM-3].
<!-- CANDIDATE:OP_1_NAMES:END -->

### DIAG-1 tail replacement

<!-- CANDIDATE:DIAG_1_TAIL:BEGIN -->
An input-envelope failure, resource failure, compiler-invariant failure, untrusted-artifact failure, backend failure, or external-tool failure is not a source-language rejection, cites no language rule, and carries no expected-terminal set.

After canonical FORM-2 succeeds for every source, semantic diagnostic selection first runs the early FN-8 structural-admission pass over every `requires_block`. Within a block, FN-8 selects its specified first invalid direct `requires_entry` or the block node for a missing final check. An invalid direct entry uses `SourceNode` at that `requires_entry` production and a `SourceCoordinate` equal to that production's complete checked half-open source extent. An empty or all-let block missing its final check uses `SourceNode` at the `requires_block` production and a `SourceCoordinate` equal to that block production's complete checked half-open source extent. These are existing owner-production extents under DIAG-1; neither case fabricates a child node, a zero-width boundary, or a terminal-only coordinate. Across blocks, the minimum tuple `(source_ordinal, byte_start, byte_end, NodePath)` of that selected location wins. Numeric fields compare ascending and NodePath compares as defined below. No declaration or use role inside an inadmissible block is classified or counted. Only complete unit-wide FN-8 admission permits role classification and its exact resource-count derivation, only complete FN-8 admission permits declaration inventory, and only complete inventory permits lexical resolution. Poison declarations and partial resolution are forbidden. An FN-8 rejection outranks every inventory or resolution rejection; an inventory rejection outranks every resolution rejection even when the later-stage event has an earlier source coordinate.

A semantic role is owned by the lowest production node whose selected right-hand side directly contains the terminal that carries the role; a role reached only through a referenced child production is owned by that child. A referenced child production means a child production node, not an external terminal predicate such as `literal`. A semantic role may occupy a complete name terminal, a complete literal terminal, or the exact TYPEID suffix of a FORM-5 generic numeric literal `0_T` or `1_T`. The suffix role's spelling excludes `_`, and its coordinate is exactly the suffix byte interval. One token may carry more than one role: for example, a law argument `0_T` has one deferred law-argument role on the complete literal and one lexical generic-type use on `T`. A struct TYPEID remains one declaration event producing two domain entries, not two events.

Within one owner node, distinct direct grammar-role carriers are ordered left to right by their complete carrier coordinates; distinct carriers with identical complete coordinates use the closed class order declaration, lexical-use, deferred-use. The zero-based carrier index is `role_ordinal`. `subtoken_ordinal` is zero for a role covering its complete carrier; embedded semantic name roles are numbered from one in byte order. The only multi-role carrier is X09/U18, where the class tie does not reorder the embedded role: a law-argument `0_T` gives its complete deferred argument `(role_ordinal, 0)` and its embedded generic-type use `(role_ordinal, 1)`. Every role has exactly one owner, class, role ordinal, and subtoken ordinal. Every declaration, lexical-use, and deferred-use event has canonical key `(source_ordinal, byte_start, byte_end, NodePath, role_ordinal, subtoken_ordinal)`. Numeric fields compare ascending. NodePath compares lexicographically by production-child ordinal, with a proper prefix first. Role and subtoken ordinals are consulted only after the complete path is equal. For a complete IDENT, TYPEID, OPNAME, REGIONID, LABEL, or literal role, the coordinate is the complete token interval, including a sigil; only the generic-numeric suffix uses a subtoken coordinate. The event's `SourceNode` names its owner production. Traversal order, allocation identity, map order, logical path, and inferred type never participate.

Declaration inventory creates candidates under this closed rank:

1. a FORM-3 reserved-name violation defined by OP-1's derived set;
2. an OWN-3 repeated REGIONID declaration within one function declaration or contract-member signature, parameters included;
3. a GRAM-10 match-binder freshness violation;
4. a TYPE-6 collision with PRE-1;
5. a TYPE-6 compilation-root duplicate or same-lexical-scope redeclaration; and
6. a TYPE-6 nested declaration shadowing a live declaration.

The stage selects the minimum declaration-event key and then the first applicable rank at that event. A FORM-3 reservation payload is `(spelling, declaration_role, reserved_class, inventory_ordinal)`. Its `spelling` is the complete declaration spelling except that a REGIONID uses its unsigiled IDENT-shaped interior while the rejection coordinate retains the complete sigiled token. Its closed declaration roles are function, named-const, parameter, let, match-binder, field, variant-field, region-parameter, and local-region. `reserved_class` is dotless-operation or mode-word. A dotless-operation ordinal is the zero-based first occurrence among distinct operation-family spellings, scanning OP-1 rows top to bottom and each `op` cell left to right and skipping every later occurrence of the same spelling; both `cvt` rows therefore name one family and one ordinal. A mode-word ordinal is the zero-based FORM-3 alternative order `wrap`, `trap`, `checked`, `sat`, `strict`. Those two reserved sets are disjoint in this version. An OWN-3 repeated-region payload is `(spelling, conflicting_region_origin)` and points to the later region declaration; OWN-3 precedes GRAM-10 in the rank even though no grammar carrier can be both a region declaration and a match binder. For the GRAM-10 violation defined by TYPE-6, the payload is `(binder_spelling, paired_field_spelling, optional_earlier_binder_origin, ordered_arm_entry_live_lexical_ident_origins)`. Earlier binders and arm-entry origins are ordered by declaration-event key. That binder does not also create a TYPE-6 duplicate or shadow candidate.

A TYPE-6 collision payload is `(spelling, ordered_nonempty_conflicts)`. Conflict domains use the fixed order lexical-IDENT, nominal-type, constructor, contract, REGIONID, LABEL. Each conflict contains its domain, declaration class, and `conflicting_origin`; conflicts within one domain use PRE-1 declaration ordinal first and then source declaration-event key. A source origin is `(NodePath, SourceCoordinate, role_ordinal, subtoken_ordinal)`; a PRE-1 origin is `(PRE-1, declaration_ordinal)`, where `declaration_ordinal` is the zero-based twenty-four-record preorder fixed by TYPE-6. A struct event may report both nominal-type and constructor conflicts in that order. Rank 4 reports only PRE-1 conflicts when the same event also conflicts with source. A PRE-1 collision points to the source declaration. Rank 5 points to the later source declaration event. Rank 6 points to the nested declaration, including one shadowing a source-later but whole-unit-visible function. Every inventory rejection uses `SourceNode` at the declaration role and has no expected-terminal set.

If inventory succeeds, every lexical use admitted by TYPE-6 or OP-1 creates one lexical-use event. The generic-numeric suffix admits a live generic TYPEID parameter; FN-3 and FORM-5, not lexical resolution, later require its numeric bound. Lexical resolution fixes only the declaration or operation-family target.

The closed declaration-class order is function, named-const, const-generic, value, generic-type, nominal-type, struct-constructor, enum-variant, contract, region, label, operation-family. TYPE-6 and OP-1 fix each lexical role's ordered admissible subset. A use's exact-spelling candidate universe contains all compilation-root entries in its grammar-selected domain and, for non-root declarations, only entries belonging to its declaration-owner chain. All sibling or expired lexical scopes within the same `fn_decl` owner participate so that an out-of-scope same-function declaration can be distinguished from absence. A contract-member signature admits declarations of that signature and its enclosing contract ancestry but not declarations owned only by a sibling member signature. A struct, enum, contract, or function generic belongs only to that declaration and its descendants. No local, generic, parameter, region, or label owned solely by an unrelated top-level declaration or function participates. PRE-1 owner-local type parameters and fields never participate in source lookup. LABEL uses instead follow the separate current-function rule below.

For one lexical-use event the closed lookup rank is:

1. the candidate universe has at least one declaration in an admissible class but its admissible visible subset is empty; cite the role-attribution table below and carry every invisible admissible origin in declaration-event order;
2. for LABEL only, the current function has at least one exact-spelling label but none declares a loop lexically enclosing the `break`; cite TYPE-6 and carry every such current-function label origin in declaration-event order; and
3. the visible admissible subset is empty and neither rank 1 nor rank 2 applies; cite the role-attribution table below.

| lexical-use role | rule cited by rank 1 or rank 3 |
|---|---|
| `type` TYPEID | TYPE-5 |
| contract bound or `conform_decl` contract TYPEID | FN-3 |
| `construct` constructor TYPEID or enum-variant-only `arm` TYPEID | TYPE-6 |
| REGIONID use | OWN-3 |
| LABEL use | TYPE-6 |
| `const` IDENT | CONST-1 |
| `cvalue` IDENT | CONST-2 |
| `pbase` IDENT | TYPE-5 |
| IDENT or OPNAME `callee` | OP-1 |
| `fn_bind` right IDENT | FN-4 |
| FORM-5 generic-numeric TYPEID suffix | FORM-5 |

A successful non-LABEL lookup has exactly one visible admissible target; a successful LABEL lookup has exactly one enclosing target. A rank-1 payload is `(spelling, lexical_use_role, ordered_admissible_classes, ordered_nonempty_invisible_origins)`. A rank-2 payload is `(spelling, lexical_use_role, ordered_nonempty_label_origins)`. A rank-3 payload is `(spelling, lexical_use_role, ordered_admissible_classes, ordered_available_classes)`, where available classes are visible exact-spelling entries in that use's candidate universe, listed once in the closed class order and possibly empty. Complete IDENT, TYPEID, OPNAME, REGIONID, and LABEL use spellings include any sigil; only the generic-numeric suffix spelling is bare `T`. This is declaration-kind resolution, not type checking. Across use events the minimum event key wins. Every resolution rejection uses `SourceNode` at the use role and has no expected-terminal set.

The dependent-declaration carriers are exactly the `field` and `vfield` declarations and the member declaration of `fn_sig`. Each is a declaration-class carrier that produces one dependent-declaration record and one declaration event for later typed owner/member checking, but none enters a resolver lookup inventory. The two field carriers participate in FORM-3's reservation inventory; the contract-member carrier does not. The deferred-use carriers are exactly the `law` name and each complete law argument, the left IDENT of `fn_bind`, the first IDENT of `fieldbind`, each `fieldinit` IDENT, and each `psuffix` IDENT. Each produces one deferred-use record for later typed owner/member checking. The lexical generic suffix inside a deferred literal law argument additionally receives its ordinary lexical-use record; this X09/U18 pair is the only same-token overlap and produces two distinct role records. In an `arm`, its leading TYPEID first resolves globally to an enum variant; later typed checking compares that variant's owning enum with the scrutinee enum, and a foreign-variant relation cites TYPE-6. The resolver does not otherwise accept or reject a dependent role's owner/member relation.

A missing whole-unit requirement is not fabricated as an inventory or lookup event. Missing `main` remains an FN-7 rejection at `BundleRoot`. Duplicate `main` names are the later-source TYPE-6 duplicate; one unique but wrong-signature `main` is a later FN-7 rejection at its source declaration. Missing or duplicate contract members, field labels, conform bindings, and law roles remain typed-dependent rejections. Selection order for semantic and target stages after lexical resolution must be separately approved with those stages.

A mechanical fix or restructuring is included exactly where the owning rule requires one. Every published diagnostic is deterministic and byte-stable.
<!-- CANDIDATE:DIAG_1_TAIL:END -->

## Closed grammar-role matrix

The matrix is exhaustive for v0.9's current grammar and FORM-5 generic numeric
subtoken. “Owner” means the DIAG-1 owner production above. One syntax token can
host two rows only where the matrix says so.

### Declaration-class roles

| ID | grammar occurrence | event/domain | visibility or owner scope | later responsibility |
|---|---|---|---|---|
| D01 | `fn_decl` IDENT | declaration; lexical IDENT/function | complete closed unit | signature typing |
| D02 | `struct_decl` TYPEID | one declaration; nominal-type plus constructor | after terminal to unit end | layout/member typing |
| D03 | `enum_decl` TYPEID | declaration; nominal-type | after terminal to unit end | enum typing |
| D04 | `variant` TYPEID | declaration; constructor | after terminal to unit end | payload/member typing |
| D05 | `contract_decl` TYPEID | declaration; contract | after terminal to unit end | contract typing |
| D06 | `const_decl` IDENT | declaration; lexical IDENT/named const | after complete item to unit end | const typing/evaluation |
| D07 | type `gparam` first TYPEID | declaration; lexical generic type overlay | after terminal through owning declaration | kind/bound typing |
| D08 | const `gparam` IDENT | declaration; lexical IDENT/const generic | after complete gparam through owner | const typing |
| D09 | `region_params` REGIONID | declaration; REGIONID | after terminal through signature/body; unique in owning function/signature | OWN-3 region checking |
| D10 | `param` IDENT | declaration; lexical IDENT/value | after complete param through requires/body; `fn_sig` has no body use | type/parameter-label checking |
| D11 | `let_stmt` IDENT | declaration; lexical IDENT/value | after complete initializer through lexical block; requires local stops before body | typing/ownership |
| D12 | `loop_stmt` LABEL | declaration; LABEL | loop body only | CFG checking |
| D13 | `region_stmt` REGIONID | declaration; REGIONID | region body only; unique throughout owning function | OWN-3 region checking |
| D14 | `fieldbind` second IDENT | declaration after GRAM-10 freshness | owning arm body after complete list | paired-field, prior-binder, and arm-entry-live collisions cite GRAM-10 |
| X01 | `field` IDENT | dependent declaration; struct field | owning struct | Decision 7 member table |
| X02 | `vfield` IDENT | dependent declaration; variant field | owning variant | Decision 7 member table |
| X03 | `fn_sig` member IDENT | dependent declaration; contract member | owning contract | Decision 7 member table |

X01 through X03 are declaration-class carriers. Each creates one dependent
declaration record and one declaration event, but enters an owner table rather
than a resolver lookup inventory. X01 and X02 also participate in FORM-3's
reservation inventory; X03 does not. D01 through D14 are the other
declaration-class carriers.

### Lexical-use and deferred-use roles

| ID | grammar occurrence | required target or deferred kind | owner | notes |
|---|---|---|---|---|
| U01 | `type` TYPEID | live generic type or nominal type | `type` | grammar role chooses type domain |
| U02 | optional bound TYPEID of type `gparam` | contract | `gparam` | first TYPEID is D07, second is U02 |
| U03 | contract TYPEID of `conform_decl` | contract | `conform_decl` | subject `type` is U01 recursively |
| U04 | `construct` TYPEID | constructor | `construct` | owner/member fields defer |
| U05 | `arm` TYPEID | enum-variant constructor only | `arm` | a struct constructor is wrong-class lookup; wrong typed scrutinee/variant relation is later TYPE-6 |
| U06 | REGIONID in `type` | live region | `type` | slice/arena regions |
| U07 | REGIONID in `mode` | live region | `mode` | shared/uniq mode |
| U08 | REGIONID `targ` | live region | `targ` | exact explicit argument |
| U09 | REGIONID in `effect` | live region | `effect` | repeated terminals receive successive role ordinals |
| U10 | REGIONID in `borrow_expr` | live region | `borrow_expr` | borrow semantics later |
| U11 | `break_stmt` LABEL | lexically enclosing loop | `break_stmt` | non-enclosing row remains explicit |
| U12 | `const` IDENT | const generic or earlier named const | `const` | integer eligibility later |
| U13 | `cvalue` IDENT | earlier named const | `cvalue` | exact type later |
| U14 | `pbase` IDENT | value binding or named const | `pbase` | function is inadmissible class |
| U15 | `callee` IDENT | derived dotless operation or top-level function | `callee` | no operand-type selection |
| U16 | `callee` OPNAME | exact operation-family identity | `callee` | complete token spelling; typed checking selects the applicable row |
| U17 | `fn_bind` right IDENT | top-level function | `fn_bind` | left side is X07 |
| U18 | `T` in literal `0_T`/`1_T` | generic type parameter | direct literal-owning production | suffix coordinate and subtoken ordinal 1; bound validity is later FN-3/FORM-5; can overlap X09 at subtoken ordinal 0 |
| X04 | `fieldinit` IDENT | construction field or named-call parameter | `fieldinit` | Decision 7 after constructor/callee |
| X05 | `fieldbind` first IDENT | variant field | `fieldbind` | second IDENT is D14 |
| X06 | `psuffix` IDENT | projected field | `psuffix` | Decision 7 after base type |
| X07 | `fn_bind` left IDENT | contract member | `fn_bind` | right IDENT is U17 |
| X08 | `law` name IDENT | closed law name | `law` | Decision 7/FN-4 |
| X09 | complete `law_arg` IDENT or literal | law argument role | `law_arg` | a generic literal also contains U18 |

U01 through U18 are lexical-use carriers. X04 through X09 are deferred-use
carriers and each creates one deferred-use record. Thus an `X` prefix does not
by itself determine a carrier's role class. Carrier ties use the closed class
order declaration, lexical-use, deferred-use. The only same-token overlap is
X09/U18: the complete X09 carrier has subtoken ordinal zero and its embedded
U18 suffix has subtoken ordinal one, so both keep one carrier role ordinal and
produce two distinct role records in that order.

Every name-shaped grammar occurrence is in the matrix. Fixed grammar words,
primitive type words, ordinary concrete numeric suffixes, punctuation, STRING,
and literal values without a generic suffix are not lexical name uses. A
complete role-classifier test must fail if an active grammar occurrence is
unlisted or listed twice, except the explicit X09/U18 overlap.

## Scope construction matrix

| scope | created by | declarations introduced | parent and exact extent |
|---|---|---|---|
| compilation unit | `program` | PRE-1, D01-D06 root entries | no parent; all records in PROG-2 order |
| declaration generic scope | `generics` of fn/struct/enum/contract | D07, D08 | compilation unit; each parameter after its declaration through the owning declaration |
| function region/signature scope | `fn_decl` | D09, D10; D09 spellings unique throughout the function | declaration generic scope when present, otherwise compilation unit; parents the function-body scope and, when present, its disjoint requires sibling |
| contract-signature scope | `fn_sig` | D09, D10; D09 spellings unique within the signature | owning contract generic scope when present, otherwise compilation unit; ends at signature terminator |
| requires lexical-block scope | `requires_block` | D11 | function region/signature scope; ends before the sibling function-body scope [FN-8] |
| function-body lexical-block scope | body braces of `fn_decl` | D11 and nested constructs | function region/signature scope; disjoint sibling of requires scope |
| nested lexical-block scope | body braces of `arm`, `loop_stmt`, or `region_stmt` | D11 and nested constructs | its distinct intermediate arm, loop-label, or local-region scope; never merged with that equal-extent parent |
| arm scope | `arm` | D14 | enclosing lexical block; parents exactly one nested body lexical-block scope |
| loop-label scope | `loop_stmt` | D12 | enclosing lexical block; parents exactly one nested body lexical-block scope |
| local-region scope | `region_stmt` | D13; spelling unique throughout owning function | enclosing lexical block; parents exactly one nested body lexical-block scope |

Member tables X01-X03 are owner tables, not lexical scopes. PROG-2 source
records and logical paths never create scopes.

## Protected-rule preservation

The candidate generator permits only these changes to exact v0.9:

1. replace the title/status prefix with the candidate header while retaining
   the former v0.9 status as the first history paragraph;
2. replace TYPE-6 exactly;
3. replace only OP-1's name/reservation paragraph, leaving every operation row
   byte-identical;
4. replace only DIAG-1's final general-failure paragraph with the semantic
   event/order text above; and
5. mechanically update exactly three self-version references inside FN-4 from
   `v0.9` to `v0.10` without changing any other FN-4 byte.

Every other byte is preserved. In particular, GRAM-1 through GRAM-11, PRE-1,
FN-1's semantics, PROG-2, the operation table, ownership/storage/effect rules,
and all protected source, expected verdict, oracle, and reference-test material
remain untouched. The generated file lives in this proposal directory and is
not an active `spec/` file. Tests reverse only the allowed edits and require
the exact pinned v0.9 bytes.

The reviewed full generated candidate identity is exactly 118,314 bytes with
SHA-256 `71073e25219455896250e15e13d1ffdbfc443c87a9b28cb9906d73a020dc33e9`.
Both generator build and check paths reject any other full-document identity.

## R-04: resolver resource contract

R-04 is an architecture proposal, not numbered language text. Decision 15
controls it.

Production resolution accepts only a validated, read-only
`ResolutionResourceProfile<'invocation>` view borrowed from the one
invocation-wide, versioned `ResourceProfile`. It never accepts a raw,
standalone, caller-forgeable `ResolutionLimits`. The view carries the parent
profile identity, the active specification identity, and maxima already
checked to be no greater than reviewed hard maxima. A raw limits value may
exist only in private unit-test support and cannot cross the production API.

The resolution view exposes these inclusive `u64` maxima in this exact order:

1. `max_declarations`;
2. `max_scopes`;
3. `max_scope_depth`;
4. `max_declaration_events`;
5. `max_lexical_uses`;
6. `max_deferred_uses`;
7. `max_spelling_bytes`;
8. `max_lookup_entries`;
9. `max_ancestry_steps`;
10. `max_node_path_depth`;
11. `max_diagnostic_origins`;
12. `max_diagnostic_paths`;
13. `max_diagnostic_path_components`;
14. `max_coverage_records`;
15. `max_work`.

Zero admits only actual zero. Counts are elements except spelling bytes,
depths, scope-ancestry steps, diagnostic path components, and work. Root scope
and empty NodePath have depth zero. `max_ancestry_steps` counts exactly one
parent edge for each non-root scope when the scope index is constructed; no
lookup performs or charges a parent walk. Interning does not reduce charged
spelling bytes.

Every statement below that spends one work unit uses one operation: first
checked-add one to the current `u64` work count, returning
`CountUnrepresentable { family: Work }` if that sum is not representable; then
compare the representable next count with `max_work`, returning
`LimitExceeded { family: Work, maximum: max_work, actual: next }` when it is
larger; then commit the next count and perform the charged action. No limit
failure requires representing `max_work + 1`.

On an FN-8 failure, none of the resolver counts in the following paragraphs is
derived. For a successfully admitted whole unit, `max_declarations` counts one
declaration record for every source D01-D14 or X01-X03 carrier plus exactly the
twenty-four PRE-1 declaration records fixed by
TYPE-6. D02 is one declaration record, not two. `max_declaration_events`
counts exactly the source D01-D14 and X01-X03 carriers; PRE-1 has no declaration
event. `max_lexical_uses` counts U01-U18 occurrences, and
`max_deferred_uses` counts X04-X09 occurrences. `max_scopes` counts distinct
scopes in the scope-construction matrix. `max_scope_depth` is the maximum
parent-edge depth of any such scope, with the root at depth zero.
`max_ancestry_steps` counts exactly one construction edge for every non-root
scope; equal-extent intermediate and body-block scopes remain distinct.

`max_spelling_bytes` is the checked sum of these logical records' exact UTF-8
role intervals: once for every admitted source occurrence D01-D14, U01-U18, or X01-X09;
once for each of the twenty-four PRE-1 declaration records; once for each of
the eighty-three distinct operation-family spellings; and once for each of the
fifty-six reservation records, namely fifty-one dotless operations and five
mode words. A complete REGIONID or LABEL includes its sigil. X09 on `0_T`
charges the complete literal and its overlapping U18 charges bare `T`. D02
charges one declaration spelling despite its two lookup entries. A dotless
operation spelling charges once as an operation family and once as a distinct
reservation record. Interned storage, event copies, lookup entries, diagnostic
payloads, and repeated `cvt` table occurrence do not add charges.

`max_lookup_entries` counts only records inserted into resolver lookup
inventories. Each admitted D01-D14 source declaration and each insertion-eligible PRE-1
analogue contributes the lookup record or records defined by its domain; D02
alone contributes two, one nominal-type and one constructor entry. X01-X03
contribute none because owner tables are not lookup inventories. PRE-1
contributes exactly eighteen lookup records: six nominal types, ten enum
variants, and two contracts; its three type parameters and three fields
contribute none. The operation inventory contributes exactly eighty-three
records, one per distinct complete operation-family spelling (`cvt` counts
once). The preflight count is the exact capacity required by this closed
insertion schema; declaration records do not become lookup entries merely by
existing.

`max_diagnostic_origins` counts one self-contained descriptor for every
retained variable payload origin, source or PRE-1; the primary SourceNode is
held by the fixed issue header and is not an origin descriptor.
`max_diagnostic_paths` counts one primary SourceNode path plus one path for
every source origin retained by the selected issue payload. PRE-1 origins add
no path. `max_diagnostic_path_components` is the checked sum of the component
counts of those paths. `max_node_path_depth` remains the per-path maximum.

`max_coverage_records` is exactly the canonical production-node count,
including the `program` root, plus the admitted matrix-role occurrence count.
Every production node has one node-disposition record. Every occurrence of
D01-D14, U01-U18, or X01-X09 in that successfully admitted unit has one
role-disposition record. A generic
literal law argument has both X09 and U18 and therefore exactly two role
records; that is the only same-token overlap. A terminal without a matrix role
has no separate coverage record.

The read-only structural preflight has two fixed subpasses. Its admission
subpass traverses `requires_block` productions in canonical mixed-topology
order and, within each, its direct `requires_entry` productions from left to
right. It spends one work unit immediately before inspecting each such block.
For each direct entry it spends one unit before reading the `requires_entry`
selected child (`doc` or `stmt`). For `stmt` it spends one further unit before
reading the statement selected child (`let_stmt`, `check_stmt`, or other); for
`let_stmt` it spends one further unit before reading its selected RHS child
(`ordinary_let_rhs`, `try_let_rhs`, or `value_match`). A nonfinal entry admits
only `stmt -> let_stmt -> ordinary_let_rhs`. An empty block selects the block
as missing its final check. In a nonempty block, the first nonfinal entry that
is not an admitted ordinary let selects that entry. If every nonfinal entry is
ordinary, a final `stmt -> check_stmt` admits the block, a final admitted
ordinary let selects the block as an all-let missing-final-check case, and any
other final shape selects that final entry. Descent stops as soon as the
current entry's shape is known, but the fixed structural scan continues through
the remaining direct entries and later blocks; the scalar issue selector keeps
the specified within-block result and then the unit-wide minimum.
It performs no role classification, maintains only the scalar best FN-8 issue,
and completes the unit-wide admission result even after finding an issue. A
work failure before an unperformed inspection wins temporally. The subpass
allocates nothing and counts no declaration, use, spelling, lookup, or role
coverage record.

If the complete admission result contains an FN-8 issue, the resolver skips
the counting subpass, all resolver-table conversions and reservations, and all
role classification and construction. It performs only the selected-
diagnostic count, `DiagnosticIssueData` conversion, reservation, and
materialization protocol below, then publishes FN-8. Only a successful
complete unit-wide admission enters the counting subpass and permits any role
classification or resolver-table count.

For a successfully admitted unit, one preflight syntax element is exactly one
production-node occurrence or terminal occurrence in the canonical finalized
mixed topology: the `program` production is visited once, then every direct
mixed child is visited once in depth-first left-to-right order. A referenced
production and its terminals are distinct elements; an external predicate does
not add an element beyond its one terminal occurrence. Before each element
visit the subpass spends one work unit, then counts the production-node
coverage record when the element is a production node. Direct terminals and
external-predicate terminals have no syntax-element count beyond that visit.
When a production opens a scope, that same charged visit first checked-adds
the scope count. It next derives the candidate scope depth: zero for the root,
or the represented parent depth checked-add one for a non-root scope; failure
to represent that candidate is `CountUnrepresentable { family: ScopeDepth }`.
It updates the measured maximum by comparison but does not test the configured
depth limit online. Finally, for a non-root scope, it checked-adds its one
ancestry construction edge. This exact scope, depth, ancestry operation order
fixes `CountUnrepresentable` precedence. The preflight ancestry count is
exactly `scopes - 1` and is known before construction. None of the three
configured maxima is tested until the complete counting pass.
Production previsit creates only production-node coverage; it never emits or
classifies a semantic role. When mixed traversal reaches a carrier terminal,
or reaches an embedded subtoken in that terminal's byte order, it spends one
additional work unit immediately before classifying and counting each carried
D01-D14, U01-U18, or X01-X09 role. A role owned by a child production is
therefore reached only during that child's traversal. Only roles on the same
carrier use the fixed class/role/subtoken tie order; X09/U18 spends two such
role visits in subtoken order. Every role-dependent capacity is therefore
derived only after complete unit-wide FN-8 admission.

The counting subpass performs no lookup and no null-sink resolution. Every
counter update uses checked `u64` arithmetic. If a permitted visit makes a
mathematical count unrepresentable, its `CountUnrepresentable` is returned at
that update; a work failure before the visit wins first. It measures maximum
canonical NodePath depth but builds no retained path arena. After all visits,
the exact `OrderingScratch` capacity is the already represented
`lookup_entries` count, copied without arithmetic; zero produces zero. Each
scratch element is one complete `LookupEntry`. Only then are structurally
known limits tested in full profile order, skipping only the three selected-
diagnostic totals, which are not yet known; work has already been enforced
temporally. This post-pass order includes `max_scopes`, `max_scope_depth`, and
`max_ancestry_steps`; none was tested online.

After every count and applicable limit succeeds, the resolver validates every
ordinary output storage in this closed order: `Declarations`, `Scopes`,
`DeclarationEvents`, `LexicalUses`, `DeferredUses`, `LookupEntries`,
`CoverageRecords`, `OrderingScratch`. For each storage it converts the `u64`
element count to `usize`, then evaluates
`Layout::array::<Element>(count)` using that storage's concrete, nonzero-sized,
safe-Rust element type. Conversion failure or a layout failure in the count
times element size, alignment, or `isize` capacity returns
`AddressSpaceExceeded { storage, requested_elements }`. Only after every
storage layout validates does the resolver create the vectors and call
`try_reserve_exact(count)` in the same storage order. The first admitted
fallible reservation failure returns
`AllocationFailure { storage, requested_elements }`. No reservation occurs
before all ordinary storage layouts have validated.

Construction continues the same work counter and uses only flat pre-counted
vectors. It first constructs the scope index in canonical scope-tree preorder.
Each scope receives a dense preorder start and exclusive subtree end; each
scope record also retains its containing declaration-owner and current-function
syntax IDs. The construction spends one work unit before writing each
scope-index record and one before examining each non-root parent edge.
Those edge examinations are exactly the already limited
`max_ancestry_steps` total. No lookup later walks a parent edge.

It next emits event records during the same depth-first mixed traversal,
spending one unit when it reaches each carrier terminal or embedded subtoken,
one before its role classification, and one before each emitted event or
declaration record. Production previsit may emit node coverage only. A child-
owned role emits during child traversal, never when its parent is visited.
SourceBundle order plus terminal byte order therefore fixes source ordinal and
complete carrier coordinate before NodePath is consulted; only roles sharing
that carrier use the fixed class/role/subtoken tie order. These are exactly the
DIAG-1 event-key components in comparison order, so the direct stream is
already sorted and no event sort, map iteration, or allocator order exists.
Dense declaration-owner and current-function IDs are assigned at their first
event in that order.

The resolver lookup inventory is one flat vector in lookup-key order. It first
appends complete entries to the already reserved `LookupEntries` vector in this
fixed sequence:
the eighteen PRE-1 entries in PRE-1 declaration/domain order, the eighty-three
operation-family entries in inventory order, then source entries in sorted
declaration-event and domain order. Each append spends one work unit before
the vector write. A non-LABEL entry belongs either to the compilation-root
partition or to exactly one dense declaration-owner partition; a LABEL entry
belongs to its one dense `FunctionLabel` partition. A lookup-entry key is
`(partition kind, partition ID, domain ordinal, exact UTF-8 spelling bytes,
origin kind, declaration-class ordinal, visibility-start event, origin order)`;
the closed origin-kind order is PRE-1, operation family, source. An
operation-family belongs to the root partition and uses its inventory ordinal
as origin order. Source visibility starts, ends, and origins use the dense
event ordinals already emitted in direct event-key order. Each entry also stores its visibility-end event and the
preorder interval of its visibility scope.

The resolver uses one fixed bottom-up stable merge engine for every inventory
ordering below. For a selected key, after the exact scratch reserve succeeds,
it initializes `OrderingScratch` with one copy of every current entry, spending
one work unit before each copy. For
`lookup_entries >= 2`, runs start at width one with scratch as source and
`LookupEntries` as destination. Each pass stably merges adjacent runs, choosing
the left entry on an equal key, then swaps the logical source and destination
and doubles the width, capped at the complete length. Each comparison uses the
lookup-key charges below and each destination-entry write spends one unit. The
number of merge passes is `ceil(log2(lookup_entries))`: an odd pass count ends
in `LookupEntries`; an even positive pass count ends in `OrderingScratch` and
performs one final forward copy back, spending one unit before each of the
`lookup_entries` writes. Zero and one perform no merge pass or final copy.
Scratch initialization, source/destination swaps, tag-free indexing, and
checked width/index calculations add no hidden comparison or allocation. No
suffix shift or insertion sort is permitted. Lookup construction is therefore
`O(D log(D + 1))` for `D = lookup_entries`, not quadratic insertion.

Before the final lookup-key ordering, that engine runs three fixed validation
orderings. `SameScopeKey` is `(eligible source declaration, partition,
declaring scope ID, domain, spelling, source event, D02 domain ordinal)`;
adjacent equal-prefix entries record the immediately earlier same-scope/root
declaration in the later declaration record's matching fixed domain slot. Each
record has one such slot per carried domain in domain order: D02 has nominal
then constructor, and every other declaration event has one. `RegionOwnerKey` is `(eligible
REGIONID, function-or-signature owner ID, spelling, source event)` and records
the immediately earlier region declaration in that owner. `ArmBinderKey` is
`(eligible match binder, arm ID, spelling, source event)` and records the
immediately earlier binder in that arm. D02 participates once in nominal then
once in constructor domain order; PRE-1, operations, and ineligible source
entries sort under disjoint flag values and create no predecessor. Every
adjacent-prefix test pays the reached key-component charges below, and each
stored predecessor ID spends one work unit before its declaration-record
write. The fourth and final engine run uses the lookup-entry key and leaves
`LookupEntries` in production query order. These constant four merge sorts and
three linear scans remain `O(D log(D + 1))` and use no second index or scratch.

The reservation
inventory is one compiled immutable flat vector already sorted by
`(exact normalized UTF-8 spelling bytes, reserved-class ordinal, inventory
ordinal)`; its required built-in identity check includes that exact order, so
runtime sorting, copying, and allocation are forbidden.
The fifty-six records consume no per-invocation storage and are not
`LookupEntries` or `OrderingScratch`; the profile nevertheless charges each
logical reservation spelling once under `max_spelling_bytes` as specified
above.

Each comparison under any of the three validation keys or the final lookup key
tests components in that key's stated order and spends
one work unit immediately before every numeric component comparison it reaches.
Exact spelling order is lexicographic over UTF-8 bytes: it spends one work unit
before every byte pair examined and, if all bytes through the shorter length
match, one further unit before the length/end decision. No spelling comparison
has a constant hidden charge. Stored dense event ordinals make visibility-start
and origin comparisons one numeric comparison each; no lookup or first-failure
origin merge rescans a NodePath. `max_spelling_bytes` bounds every individual
stored spelling interval and `max_work` bounds the repeated comparison work.
Visibility-end and scope-interval metadata do not participate in ordering.
Only complete `LookupEntry` values use `OrderingScratch`; the borrowed
reservation vector requires no second sort scratch.

Declaration inventory then processes declaration events directly in event-key
order and tests ranks 1 through 6 in rank order, stopping at the first failing
event/rank. It spends one work unit before every applicable rank check. Rank 1
uses the exact reservation prefix searches below for every OP-1 reservation-
eligible role, including X01 field and X02 variant-field declarations even
though they have no lookup entry. Rank 2 reads the precomputed
`RegionOwnerKey` predecessor for a REGIONID and spends one unit before its
self-ID exclusion. Rank 3 compares a match binder with its paired field using
the exact byte-comparison charges, reads and self-excludes its `ArmBinderKey`
predecessor, and performs the interval-index query below at the stored arm-entry
event over root/current-owner lexical-IDENT groups. These three checks run in
the exact GRAM-10 payload order: paired field, earlier binder, then live arm-
entry declarations.

For each declaration domain carried by the event, rank 4 binary-searches only
root/PRE-1 groups, rank 5 reads the `SameScopeKey` predecessor and verifies the
same root or lexical scope from that domain's matching predecessor slot, and
rank 6 runs only for a non-root nested declaration and queries the root plus
the declaration's grammar-bounded proper enclosing-scope owner chain at the
declaration coordinate. Rank 6 excludes the current declaration and every
same-scope candidate; root events never run it. Every candidate
comparison spends one work unit before explicit self-ID exclusion. A whole-
unit source function has the full-unit interval even when its source event is
later, so the rank-6 query detects a nested declaration that would shadow that
later function. D02 performs each rank's nominal query before its constructor
query. LABEL and REGIONID use their `FunctionLabel` and function/signature-
owner partitions respectively; unrelated owners are never examined.

Each inventory binary-search iteration pays one probe plus the exact reached
key/spelling charges. A fixed paired-field or interval test spends one unit
before the test. If a predecessor, PRE-1 group, duplicate group, or live-shadow
group makes the current rank fail, selection retains only the scalar issue plan
and the constant matched-range bounds already produced by that check.
Selection does not scan a matched entry, merge heads, self-exclude an entry, or
count an origin. The exact diagnostic origin iterator below performs those
operations later. This rule applies uniformly to inventory ranks 1 and 2,
OWN-3, and every GRAM-10 origin group as well as to the lexical failures
described below. Thus complete inventory checking remains
`O(D log(D + 1))`, with no alternate map, owner walk, per-event equal-range
scan, or selected-failure planning scan.

For a non-LABEL lexical use, the applicable partition list is the root followed
by its non-root declaration-owner chain. The grammar bounds that chain at two:
a `contract_decl` generic owner plus one `fn_sig` owner, or otherwise one
top-level declaration/function owner. For every applicable partition, each
member of the role's closed constant admissible-class set, and each applicable
closed origin kind, the resolver uses
lower-bound and upper-bound binary searches for the exact
`(partition kind, partition ID, domain, spelling, origin kind, class)` group, then one
upper-bound search inside that group for the greatest visibility start not
after the use. Every iteration selects `mid = lo + (hi - lo) / 2` with floor
division, spends one work unit before the probe, and then pays the reached key-
component comparisons above. It spends one further work unit before testing
the candidate's visibility end and one before testing the use scope's preorder
against the stored scope interval.

After inventory success, TYPE-6 no-live-shadowing guarantees that visibility
intervals in the same partition/domain/spelling/class group do not overlap;
the inventory also rejects cross-class live shadowing. Therefore the greatest-
start candidate plus those two constant-time tests finds the unique visible
target, if one exists. An unrelated function or signature has a different
partition and is never probed or scanned. Root visibility, exact declaration-
before-use starts, signature terminators, and lexical-scope ends are all
represented by the same stored start/end and preorder-interval fields.

Uses are resolved in direct event-key order. Only the first failing use builds
a scalar payload plan. If an admissible exact group is nonempty but no
admissible entry is visible, rank 1 retains only the constant number of
matched-range bounds and performs no planning scan. The diagnostic count and
materialization runs later use the exact origin iterator below over those
ranges. If no
admissible group exists, rank 3 obtains visible available classes by the same
binary searches over the closed class set and stores them as a fixed class
bitset in the issue header. No successful use and no later failing use performs
an origin-planning scan.

LABEL uses query one `FunctionLabel` partition keyed by the precomputed current-
function ID and exact spelling. Entries are ordered by visibility start and
carry their loop's preorder/subtree interval. One group-prefix search and one
greatest-start search, charged as above, plus one constant-time interval test
finds the unique enclosing label. TYPE-6 no-live-shadowing makes live same-
spelling loop intervals non-overlapping. If the exact current-function group is
nonempty but no interval encloses the use, the first failing LABEL use takes
rank 2 and retains that group's bounds without scanning it; the exact
diagnostic origin iterator later scans it during counting and descriptor
materialization. An empty group takes rank 3. Labels in another function are
never examined.

Every reservation query uses lower-bound and upper-bound binary searches over
the immutable reservation vector on its normalized-spelling prefix. Each
iteration uses the same midpoint rule, spends one unit before its probe, and
then uses the same per-byte plus length/end charges for its exact normalized-
spelling comparison. The validated inventory
makes the resulting range empty or one record; examining that record spends
one unit.

Let `D` count declaration, scope-index, and lookup records, `U` count lexical
and deferred-use records, `B` count the UTF-8 byte-pair and matched-prefix end
decisions actually charged by all spelling comparisons, and `Q` count elements
in the selected `DiagnosticIssueData` stream (zero on completion). After the
mandatory linear syntax traversal, scope/owner indexing is `O(D)`, lookup
construction performs `O(D log(D + 1))` record comparisons, all successful and
pre-failure queries perform `O(U log(D + 1))` record probes, and the diagnostic
protocol performs exactly two `O(D)` origin scans plus `O(Q)` stream work. The
constant factor two is absorbed by the linear term. Therefore the honest
output-sensitive post-traversal bound is
`O((D + U) log(D + 1) + B + Q)`. Decision 6's indexed record-lookup bound is
the first term; `B` exposes rather than hides arbitrary legal name length, and
`Q` exposes origin/path-component output. No repeated unrelated-owner scan or
scope-depth factor is hidden in any term. No standard sort, hash table, tree map, alternative
search, node-allocating container, hidden comparison, or hidden allocation is
admitted. Allocator behavior and traversal allocation identity cannot select
output or failure.

Resolver tables store dense syntax-node, scope, declaration-owner, and current-
function IDs, not NodePaths. Scope ancestry is consumed once into preorder/
subtree intervals during index construction and is never walked during a
lookup.

After selecting a source issue, including an FN-8 issue selected by admission,
the resolver creates only a scalar issue plan plus the constant number of
matched group ranges described above. It does not retain a variable payload or
pre-scan or retain origin counts. Constant ranges are consumed while the
unpublished resolver tables still exist and before those tables can be
discarded.

Every diagnostic family uses one exact ordered origin iterator. The issue's
closed payload schema supplies a constant sequence of fixed-origin slots and
matched-range slots in normative payload order. A matched-range slot uses a
fixed-head merge over its constant number of already ordered ranges; PRE-1
origins use declaration ordinal and precede source origins, and source origins
use stored dense event ordinal. The iterator spends one work unit before each
range entry it examines, one before each reached head comparison, one before
each explicit self-ID exclusion, and one before accepting each fixed or range
origin. Fixed origins have no range-entry or head-comparison charge. This same
iterator definition applies to inventory ranks 1 and 2, GRAM-10, OWN-3, and
lexical ranks 1 and 2. It uses only its constant heads and the scalar issue
plan; it never sorts, walks a NodePath to order origins, or allocates.

The selected-diagnostic counting pass first spends one work unit for the
primary SourceNode, converts its canonical NodePath component length to `u64`,
checked-adds one to the path count, and checked-adds that depth to the component
count. It then runs the exact origin iterator once. For each accepted origin it
checked-adds one diagnostic origin; for a source origin it also converts the
origin path depth, updates the selected maximum by comparison, checked-adds one
path, and adds the depth to the component count. A PRE-1 origin adds its
descriptor count but no path. The primary node is not an origin descriptor.

After that complete pass, limits are tested in profile order:
`max_node_path_depth`, `max_diagnostic_origins`, `max_diagnostic_paths`, then
`max_diagnostic_path_components`. The selected depth check runs even when a
successful-admission counting subpass already proved the whole-unit depth.
The resolver then derives the exact stream count by checked-adding, in this
order, `1 + diagnostic_origins`, then `diagnostic_paths`, then
`diagnostic_path_components`. At the late `DiagnosticIssueData` storage
position after `OrderingScratch`, it converts that `u64` element count to
`usize`, then evaluates `Layout::array::<DiagnosticIssueElement>(count)` for
the concrete, nonzero-sized, safe-Rust stream element. A conversion or layout
size/alignment/`isize` failure returns
`AddressSpaceExceeded { storage: DiagnosticIssueData, requested_elements }`.
Only after that layout validates does it call `try_reserve_exact(count)`; an
admitted fallible reservation failure returns
`AllocationFailure { storage: DiagnosticIssueData, requested_elements }`.

`DiagnosticIssueData` is one closed self-contained element stream in this
order: one fixed `IssueHeader`; one `OriginDescriptor` per retained payload
origin; the primary SourceNode's `PathHeader` immediately followed by its path
components; then, for each source origin in descriptor order, its `PathHeader`
immediately followed by its path components. The
header contains the rule/reason, primary SourceNode and checked coordinate,
exact element counts, and one closed reason payload: FN-8 shape kind; FORM-3
spelling handle/declaration role/reserved class/inventory ordinal; OWN-3
spelling handle; GRAM-10 binder-spelling and paired-field-spelling handles;
TYPE-6 collision spelling handle; or lexical spelling handle/role/admissible-
class bitset/available-class bitset. The GRAM-10 variant therefore carries both
required spellings, not one generic spelling slot. Handles name input-owned
intervals (including the normalized REGIONID interior when required), and no
variant copies spelling bytes. An origin descriptor contains its payload role, domain and
declaration class plus either a complete source origin `(SourceNode,
SourceCoordinate, role_ordinal, subtoken_ordinal)` or a complete PRE-1 origin
`(PRE-1, declaration_ordinal)`. A path header contains its component start and
count. No element contains a declaration, scope, lookup, or partial resolver-
table reference.

After reservation, materialization spends one work unit before writing the
`IssueHeader`, reruns the exact origin iterator once, with exactly the same
range-entry, head-comparison, self-exclusion, and accepted-origin charges, and
spends one additional work unit before writing each resulting
`OriginDescriptor`. It then spends one work unit before the primary
`PathHeader` write and one before each primary component write. Finally it
iterates the just-written origin descriptors exactly once in descriptor order,
spending one work unit before every descriptor read. A PRE-1 descriptor adds
nothing further. For a source descriptor it spends one work unit before its
`PathHeader` write and one before each component write. Thus selection performs
no matched-entry scan, the origin iterator runs exactly twice, and path
materialization performs no third resolver-table scan. Any count, limit,
conversion, layout, reserve, or work failure publishes no partial stream,
resolver table, issue, or capability.

`CountUnrepresentable.family` uses one closed `ResolutionCountFamily`, not a
caller string. Its first fifteen members are the profile families in profile
order. One derived-only member follows: `DiagnosticIssueElements`. Every
checked sum or product has exactly one attribution. Adding a source or PRE-1
declaration, scope, declaration event, lexical use, deferred use, spelling
interval, lookup entry, ancestry edge, path-depth candidate, diagnostic origin,
diagnostic path, diagnostic path component, coverage record, or work unit is
attributed to its same-named profile family. In particular, the twenty-four
PRE-1 additions use `Declarations`; the eighteen PRE-1 and eighty-three
operation-family lookup additions use `LookupEntries`; every source, PRE-1,
operation-family, and reservation spelling-byte addition uses `SpellingBytes`;
and production-node plus admitted-role coverage additions use
`CoverageRecords`. Maximum depth is selected by comparison; only checked
representation of a candidate depth can fail, as `NodePathDepth` or
`ScopeDepth` respectively.

During selected-diagnostic counting, converting a canonical NodePath component
length to `u64` is `NodePathDepth`; every checked origin addition is
`DiagnosticOrigins`; every checked path addition is `DiagnosticPaths`; and
adding each path depth to the component sum is `DiagnosticPathComponents`.
Each of the three header-inclusive stream additions is
`DiagnosticIssueElements`. `OrderingScratch` copies the already represented
`LookupEntries` capacity unchanged and introduces no count arithmetic. Lookup
sort widths and indices are calculated only after both storages convert to the
host length; capped doubling and the common exact length prove every run,
midpoint, boundary, and destination index representable. No unlisted aggregate,
multiplication, or fallback attribution is permitted. Within preflight and
diagnostic counting, failures occur at the named checked operation in the fixed
operation order just stated; temporal work failure still wins before an
unperformed operation.

The production outcome family is closed:

```text
Complete(ResolutionCompleteUnit)
SourceIssue(ResolutionRejectedUnit)
InvocationFailure(ResolutionInvocationFailure)
ResourceFailure(ResolutionResourceFailure)
CompilerFailure(ResolutionCompilerFailure)
```

`ResolutionRejectedUnit` owns the consumed exact `CanonicalSyntaxUnit` plus its
complete `DiagnosticIssueData` stream and owns no partial resolver table.
Source-coordinate, spelling, SourceNode, and path accessors borrow that owned
syntax through `&self`; origin descriptors and paths never reference a dropped
private scope, declaration, lookup, or coverage table. On success only,
`ResolutionCompleteUnit` owns the syntax and complete resolver tables.

`ResolutionInvocationFailure` has exactly
`SpecificationMismatch { syntax, resolver }` and
`ResourceProfileMismatch { invocation, resolution_view }`; the outcome line
above abbreviates this closed enum. Before tree traversal, specification
identity is checked first and parent-profile identity second. A mismatch is
`InvocationFailure`, never a source rejection or compiler invariant. Only
after both pass does the resolver validate its compiled PRE-1 inventory, then
its compiled operation-family inventory, and then its compiled reservation
inventory against its own active specification identity. Their first mismatch is
`ResolutionCompilerFailure::BuiltInInventoryMismatch { family }`, with family
order `Prelude`, `Operations`, `Reservations`; it is not source input or caller
invocation failure. `Reservations` validates exactly fifty-six immutable
records in their required sorted order before any source traversal.

The resource-failure variants are
`LimitExceeded { family, maximum, actual }`,
`CountUnrepresentable { family }`,
`AddressSpaceExceeded { storage, requested_elements }`, and
`AllocationFailure { storage, requested_elements }`. The exact overall order
is invocation identity, built-in identity, and the complete FN-8 admission
scan. A selected FN-8 then takes only the diagnostic branch stated above. A
successful admission continues with temporal counting work/count failure,
post-count limits in profile order, then complete host-length and concrete
layout validation in storage order, then fallible exact reservation in storage
order, and then the first canonical construction failure. For every selected
source issue, the diagnostic count limits, host conversion and concrete layout
validation, `DiagnosticIssueData` reservation, and materialization follow
issue selection as specified above and can replace the unpublished issue with
a resource failure. The closed storage order is
`Declarations`, `Scopes`, `DeclarationEvents`, `LexicalUses`, `DeferredUses`,
`LookupEntries`, `CoverageRecords`, `OrderingScratch`, `DiagnosticIssueData`.
Every requested value is a count of that storage's elements. No failure
publishes partial tables, paths, issue, or capability.

This packet deliberately selects no numeric hard maximum. Decision 15 requires
reviewed numerical evidence and committed hard maxima before resolver
implementation. Installing those values and their evidence is an explicit
first pre-resolver stop; schema-only approval is insufficient.

## Corrected architecture consequences C-01 through C-06

### C-01: one canonical tree and exact mixed topology

`CanonicalSyntaxUnit` lends a read-only view with opaque runtime-local node and
terminal handles. The finalized topology must retain each production node's
direct children as one checked interleaved sequence of production and terminal
elements in grammar order. The linear finalizer already observes this order;
it must retain and resource-account it rather than reconstruct it by reparsing
or scanning terminal extents.

This is a replacement, not a second edge store. The successor frontend replaces
`FinalizeLimits.max_child_edges`, `FinalizeLimit::ChildEdges`,
`FinalizeStorage::ChildEdges`, and the production-only child vector with
`max_mixed_elements`, `FinalizeLimit::MixedElements`,
`FinalizeStorage::MixedElements`, and one retained flat mixed-child vector at
the same limit and storage-order positions. Its exact count is
`(production_nodes - 1) + terminals`, equivalently the complete private parsed
derivation-element count minus the `program` root. The finalizer derives that
count from the complete private derivation with checked arithmetic before any
topology allocation, tests the inclusive limit at the former child-edge field
position, converts the exact count from `u64` to `usize`, and evaluates
`Layout::array::<MixedElement>(count)` for the concrete, nonzero-sized,
safe-Rust record before any reserve. Conversion or layout
size/alignment/`isize` failure returns the successor finalizer's
`AddressSpaceExceeded { storage: MixedElements, requested_elements }` at the
former `ChildEdges` storage-order position. Only after that layout validates
does it call `try_reserve_exact(count)` there; an admitted fallible failure is
the successor's
`AllocationFailure { storage: MixedElements, requested_elements }`, as required
by Decision 15, rather than the predecessor's `StorageUnavailable` variant.
The successor's numerical maximum is separately evidence-selected and owner-
approved; it is not inherited by renaming the current maximum.

Each mixed record is exactly `Production { node, production_child_ordinal }`
or `Terminal { terminal }`. A `NodeRecord` stores its mixed start/count and its
production-child count. No separate production-edge vector remains; terminal
records remain the one terminal metadata store. The finalizer spends one of
its existing checked work units immediately before each mixed-record write.
Direct-child iteration borrows the retained mixed range, while production-only
iteration filters that same range and reads the stored unchanged production-
child ordinal. Neither path scans terminal extents, reparses, reconstructs, or
allocates another edge sequence. The migrated successor frontend must
reproduce every existing finalizer/compiler-invariant gate under the new
representation before it can become active.

Mixed-element ordinal and DIAG-1 `NodePath` ordinal are distinct. Existing
NodePath components remain zero-based **production-child** ordinals, ignoring
direct terminals. The refinement adds an element ordinal for the interleaved
view and does not renumber a single existing NodePath. Each production child
retains both its production-child ordinal and its mixed-element ordinal. A
terminal view exposes its source token and selected terminal predicate. Handles
cannot escape or be used without the borrowed unit and are never portable
identity. The seam adds no AST, semantic field, or mutable access.

### C-02: one owned, non-self-referential resolution capability

`ResolutionCompleteUnit` consumes and owns the exact successor-bound
`CanonicalSyntaxUnit`, scope tree, declaration inventory, resolution records,
dependent-role records, and coverage. Resolver-owned IDs are private dense
integer newtypes. `OwnedSyntaxNodeId` indexes the immutable topology inside the
owned canonical unit; declaration, scope, use, and coverage IDs index
resolver-owned vectors. They contain no Rust borrow, pointer, reference,
NodePath, source address, or owner object, and therefore do not make the result
self-referential. Public accessors require `&self`, validate the index and kind,
and return owner-scoped views. Tables and syntax cannot be paired with another
unit. Portable artifact references remain later structural identities.

The source-rejection branch instead returns `ResolutionRejectedUnit`, which
owns that exact consumed syntax and the one complete self-contained
`DiagnosticIssueData` stream described by R-04. It contains no partial resolver
table; all coordinate, spelling, origin, and path views borrow its owned syntax
through `&self`.

Only the private complete constructor can issue the capability. Completeness
means every canonical production node, including the `program` root, has
exactly one node-disposition record and every actual matrix-role occurrence
has exactly one role-disposition record. X09/U18 on one generic literal law
argument is the sole same-token overlap and produces exactly two distinct role
records. Every lexical use has exactly one target; every dependent role has one
closed dependent-declaration or deferred-use record; and nothing is missing,
duplicated, or poisoned. The public outcome
includes `InvocationFailure` as specified by R-04. The capability contains no
types, call edges, CFG, ownership, effect, optimizer, artifact, backend,
executable, or release authority.

### C-03: all signatures before any body

The symbolic tranche first checks declaration schemas under their exact
declaration-before-use rules, then checks every top-level source function
signature as one complete batch, seals that environment, and only then checks
any body. An X03 contract-member name remains only in its owning contract's
member table and never receives A-01 whole-unit function-name visibility.
Top-level D01 functions nevertheless remain whole-unit-visible while D10
parameters inside that member signature are checked, so those parameters may
not shadow a function. No body traversal can create or repair a signature.

### C-04: one graph authority, two call graphs

Decision 7 emits checked local typed-call records and no graph. Decision 9 is
the sole call-graph/SCC authority and constructs exactly two stage-specific
graphs: `TemplateCallGraph` from template records and `ConcreteCallGraph` from
concrete records. These are two graph instances under one authority, not two
authorities. Template and concrete checking share local judgment definitions
but build their own records and CFGs. Replay independently traverses decoded
records and invokes the same judgments; it never reuses producer state. A
provenance-equation SCC is a distinct non-call record family.

### C-05: structural CFG before cleanup

`ConcreteControlFlowUnit` first records complete normal, trap, check, and
scope-exit topology without live-value cleanup. After provenance and ownership
close, the later ownership step attaches exact drop, free, and arena-release
operations to normal exit edges. Trap/abort edges have no cleanup. Placeholder
cleanup slots and empty plans with future authority are forbidden. Template
effects still close before template semantic coverage; concrete effects close
during whole-unit completion.

### C-06: report premises, not final reports

Phase 5 retains trap origins, logical-call premises, complete check-site
inventory with baseline retained-check obligations, lifetime dispositions, and
report coverage. It does not emit final DIAG-3 bytes, final
retained/eliminated status, or `artifact_hash`. Those depend on later artifact
projection, empty-or-verified overlay selection, and final compilation
identity. Report premises grant no optimizer authority.

## Exact approvals available from this packet

Conceptual approval of an earlier packet is not approval of these corrected
bytes. This packet contains exact material on which the owner can now rule:

1. the exact v0.10 header, TYPE-6, OP-1, DIAG-1, and three mechanical FN-4
   self-version substitutions generated here;
2. the three TYPEID domains, including struct dual entry, cross-domain spelling
   reuse, PRE-1 placement, visibility intervals, and diagnostic conflict order;
3. the complete selected closed OP-1 reservation declaration list, including named
   consts and requires-block lets while explicitly excluding const generics,
   LABELs, and contract-member names;
4. the complete grammar-role and scope matrices, including the overlapping
   law-argument/generic-numeric subtoken roles;
5. semantic event ownership, role ordering, payloads, stage/rank order, and
   missing/duplicate whole-unit behavior;
6. R-04's invocation-wide validated profile view, fields, counts, failure
   family, and failure order;
7. C-01's no-duplicate-edge mixed-topology replacement, unchanged production-
   child NodePath ordinals, exact `MixedElements` count/limit/storage/work
   migration, reproduced frontend gates, and separately approved numerical
   maximum;
8. C-02's owned dense-ID model and `InvocationFailure`, and C-03 through C-06;
9. the reproduced protected-surface census, which records only the pinned
   conformance/codegen R-01 namespace/generic and R-02 reservation
   intersections; it does not prove semantic replay, rule/location stability,
   or zero protected-verdict changes, and no protected byte is proposed for
   change; and
10. the two abstract diagnostic-order evidence models and their cases, which
    support only their documented critical role subset, ordering, failure
    closure, and exact/one-over resource behavior and do not claim source
    projection, full matrix coverage, production allocation, or hard maxima.

## Later stops not available for approval from this packet

Even if every exact item above is approved, resolver implementation remains
stopped on:

1. evidence-selected numerical hard maxima and their separate owner approval
   under Decision 15;
2. exact active-target migration and identity rebinding, grammar/source
   evidence reproduction under the v0.10 identity, live-reference updates,
   guarded `make approve-spec REASON="..."` installation, and the ordinary
   repository gates; and
3. only after both stops close, separately scoped authorization to implement
   the resolver tranche.

No numerical profile values are proposed here. No protected expectation is
changed. Any disagreement about the exact rows above is an approval blocker,
not implementation discretion.
