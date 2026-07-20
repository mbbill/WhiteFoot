#!/usr/bin/env python3
"""Audit the first exact statement-scoped unique-child reborrow slice."""

import ctypes
import tempfile
from pathlib import Path

from test_lexer import build_library
from test_parser import AST_NONE, children_of
from test_semantic_body import (
    AST,
    BODY_CLEAN,
    BODY_UNSUPPORTED,
    SemanticBodyReport,
    assert_output_guards,
    parsed,
)
from test_semantic_unit import (
    CAPABILITY_ACYCLIC,
    CAPABILITY_UNSUPPORTED,
    FIX_NONE,
    RULE_NONE,
    assert_no_capability_diagnostic,
    configure,
    invoke_dispatch,
    make_work,
    top_level_functions,
)


REBORROW_WRITER = (
    b"struct ReborrowChild {\n"
    b"  value: u64;\n"
    b"}\n"
    b"struct ReborrowParent {\n"
    b"  first: ReborrowChild;\n"
    b"  second: ReborrowChild;\n"
    b"}\n"
    b"fn reborrow_child_reset ['c] (child: &uniq 'c ReborrowChild) "
    b"-> own unit writes('c) {\n"
    b"  set deref(child).value = 0_u64;\n"
    b"  return unit;\n"
    b"}\n"
    b"fn reborrow_parent_reset ['p] (parent: &uniq 'p ReborrowParent) "
    b"-> own unit writes('p) {\n"
    b"  region 'first_call {\n"
    b"    reborrow_child_reset(child: &uniq 'first_call "
    b"deref(parent).first);\n"
    b"  }\n"
    b"  region 'second_call {\n"
    b"    reborrow_child_reset(child: &uniq 'second_call "
    b"deref(parent).second);\n"
    b"  }\n"
    b"  return unit;\n"
    b"}\n"
)


def assert_reborrow_boundary(library):
    def classify(source):
        case = parsed(library, source)
        function = top_level_functions(case)[-1]
        work = make_work(library, case[5].count)
        kind, report = invoke_dispatch(library, case, function, work)
        return case, function, work, kind, report

    def assert_clean(source=REBORROW_WRITER):
        case, function, work, kind, report = classify(source)
        assert (kind, report.status, report.function, report.related) == (
            CAPABILITY_ACYCLIC,
            BODY_CLEAN,
            function,
            AST_NONE,
        ), (kind, report.status, report.function, report.related)
        assert_no_capability_diagnostic(report)
        assert_output_guards(work)
        return case, function

    def assert_unsupported(source):
        _, function, work, kind, report = classify(source)
        assert (kind, report.status, report.function) == (
            CAPABILITY_UNSUPPORTED,
            BODY_UNSUPPORTED,
            function,
        ), (kind, report.status, report.function, report.related)
        assert_no_capability_diagnostic(report)
        assert_output_guards(work)

    assert_clean()

    # The outer function is an exact writes-only unit writer over one unique
    # struct parent and one declared caller region.
    assert_unsupported(
        REBORROW_WRITER.replace(b"writes('p) {", b"pure {")
    )
    assert_unsupported(
        REBORROW_WRITER.replace(b"writes('p) {", b"writes('p), traps {")
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"parent: &uniq 'p ReborrowParent",
            b"parent: &'p ReborrowParent",
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(b"['p]", b"['p, 'q]", 1)
    )

    # The child region is local to the one expression statement, distinct from
    # the caller region, and spelled identically at its borrow site. Region
    # names remain unique across the function.
    assert_unsupported(
        REBORROW_WRITER.replace(b"'first_call", b"'p")
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"&uniq 'first_call deref(parent).first",
            b"&uniq 'second_call deref(parent).first",
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(b"'second_call", b"'first_call")
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"reborrow_child_reset(child: &uniq 'first_call",
            b"reborrow_child_reset<'first_call>(child: &uniq 'first_call",
        )
    )

    # This slice admits one unique child of a direct field. Shared children,
    # whole-parent children, deeper suffixes, and bound call results remain
    # separate profiles.
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"&uniq 'first_call deref(parent).first",
            b"&'first_call deref(parent).first",
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"&uniq 'first_call deref(parent).first",
            b"&uniq 'first_call deref(parent)",
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"deref(parent).first);",
            b"deref(parent).first.value);",
            1,
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"    reborrow_child_reset(child: &uniq 'first_call "
            b"deref(parent).first);",
            b"    let ignored: own unit = reborrow_child_reset("
            b"child: &uniq 'first_call deref(parent).first);",
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"    reborrow_child_reset(child: &uniq 'first_call "
            b"deref(parent).first);",
            b"    reborrow_child_reset(child: &uniq 'first_call "
            b"deref(parent).first);\n"
            b"    reborrow_child_reset(child: &uniq 'first_call "
            b"deref(parent).first);",
        )
    )

    # The callee must have one unique parameter in one formal region, return
    # own unit, declare only writes(formal), and exhibit that exact flat write.
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"child: &uniq 'c ReborrowChild",
            b"child: &'c ReborrowChild",
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(b"writes('c) {", b"reads('c) {")
    )
    assert_unsupported(
        REBORROW_WRITER.replace(b"writes('c) {", b"writes('c), traps {")
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"  set deref(child).value = 0_u64;\n", b"", 1
        )
    )
    assert_unsupported(
        REBORROW_WRITER.replace(
            b"child: &uniq 'c ReborrowChild",
            b"child: &uniq 'c ReborrowParent",
        )
    )

    # Multiple sibling children require their own OWN-7 overlap proof. Both a
    # disjoint pair and an overlapping pair stay unsupported in this slice.
    pair_callee = (
        b"fn reborrow_pair ['c] (left: &uniq 'c ReborrowChild, "
        b"right: &uniq 'c ReborrowChild) -> own unit writes('c) {\n"
        b"  set deref(left).value = 0_u64;\n"
        b"  set deref(right).value = 0_u64;\n"
        b"  return unit;\n"
        b"}\n"
    )
    pair_parent = (
        b"fn reborrow_pair_parent ['p] (parent: &uniq 'p ReborrowParent) "
        b"-> own unit writes('p) {\n"
        b"  region 'pair_call {\n"
        b"    reborrow_pair(left: &uniq 'pair_call deref(parent).first, "
        b"right: &uniq 'pair_call deref(parent).second);\n"
        b"  }\n"
        b"  return unit;\n"
        b"}\n"
    )
    declarations = REBORROW_WRITER.split(b"fn reborrow_child_reset", 1)[0]
    assert_unsupported(declarations + pair_callee + pair_parent)
    assert_unsupported(
        declarations
        + pair_callee
        + pair_parent.replace(b"deref(parent).second", b"deref(parent).first")
    )

    def assert_direct_reader_mutation_rejected(mutate):
        case, function = assert_clean()
        mutate(case, function)
        work = make_work(library, case[5].count)
        report = SemanticBodyReport(99, 123, 456, 99, 99, 789)
        library.semantic_reader_run(
            case[1],
            ctypes.byref(case[3]),
            ctypes.byref(case[5]),
            ctypes.byref(case[9]),
            function,
            ctypes.byref(work[6]),
            ctypes.byref(report),
        )
        assert (report.status, report.rule, report.fix) == (
            BODY_UNSUPPORTED,
            RULE_NONE,
            FIX_NONE,
        )
        assert_output_guards(work)

    def reborrow_nodes(case, function):
        columns = case[4]
        outer_block = next(
            node
            for node in children_of(columns, function)
            if columns[0][node] == AST["AstBlock"]
        )
        first_region = children_of(columns, outer_block)[0]
        local_region, inner_block = children_of(columns, first_region)
        expression_statement = children_of(columns, inner_block)[0]
        call = children_of(columns, expression_statement)[0]
        named_argument = children_of(columns, call)[0]
        borrow = children_of(columns, named_argument)[0]
        child_region, field = children_of(columns, borrow)
        deref_place = children_of(columns, field)[0]
        parent_place = children_of(columns, deref_place)[0]
        callee = top_level_functions(case)[0]
        callee_children = children_of(columns, callee)
        callee_name = callee_children[0]
        callee_regions = callee_children[1]
        callee_formal_region = children_of(columns, callee_regions)[0]
        callee_parameter = callee_children[2]
        callee_mode, callee_type = children_of(columns, callee_parameter)
        callee_mode_region = children_of(columns, callee_mode)[0]
        callee_writes = callee_children[5]
        callee_writes_region = children_of(columns, callee_writes)[0]
        outer_children = children_of(columns, function)
        outer_regions = outer_children[1]
        outer_formal_region = children_of(columns, outer_regions)[0]
        outer_parameter = outer_children[2]
        outer_mode = children_of(columns, outer_parameter)[0]
        outer_mode_region = children_of(columns, outer_mode)[0]
        parent_struct = next(
            node
            for node in children_of(columns, case[5].root)
            if columns[0][node] == AST["AstStructDecl"]
            and any(
                columns[0][child] == AST["AstField"]
                and bytes(case[0][columns[2][child] : columns[3][child]])
                == b"first: ReborrowChild;"
                for child in children_of(columns, node)
            )
        )
        parent_field = next(
            child
            for child in children_of(columns, parent_struct)
            if columns[0][child] == AST["AstField"]
            and bytes(case[0][columns[2][child] : columns[3][child]]).startswith(
                b"first:"
            )
        )
        parent_field_type = children_of(columns, parent_field)[0]
        return {
            "first_region": first_region,
            "local_region": local_region,
            "call": call,
            "named_argument": named_argument,
            "borrow": borrow,
            "child_region": child_region,
            "field": field,
            "parent_place": parent_place,
            "callee_name": callee_name,
            "callee_parameter": callee_parameter,
            "callee_type": callee_type,
            "callee_formal_region": callee_formal_region,
            "callee_mode_region": callee_mode_region,
            "callee_writes_region": callee_writes_region,
            "outer_parameter": outer_parameter,
            "outer_formal_region": outer_formal_region,
            "outer_mode_region": outer_mode_region,
            "parent_field": parent_field,
            "parent_field_type": parent_field_type,
        }

    def redirect_head(target, source):
        def mutate(case, function):
            nodes = reborrow_nodes(case, function)
            case[4][1][nodes[target]] = case[4][1][nodes[source]]

        return mutate

    def borrow_kind_shared(case, function):
        nodes = reborrow_nodes(case, function)
        case[4][0][nodes["borrow"]] = AST["AstSharedBorrow"]

    def named_argument_cycle(case, function):
        nodes = reborrow_nodes(case, function)
        case[4][6][nodes["named_argument"]] = nodes["named_argument"]

    for mutate in (
        redirect_head("local_region", "child_region"),
        redirect_head("child_region", "local_region"),
        redirect_head("call", "callee_name"),
        redirect_head("named_argument", "callee_parameter"),
        redirect_head("parent_place", "outer_parameter"),
        redirect_head("field", "parent_field"),
        redirect_head("callee_type", "parent_field_type"),
        redirect_head("callee_mode_region", "callee_formal_region"),
        redirect_head("callee_writes_region", "callee_formal_region"),
        redirect_head("outer_mode_region", "outer_formal_region"),
        borrow_kind_shared,
        named_argument_cycle,
    ):
        assert_direct_reader_mutation_rejected(mutate)


def main():
    with tempfile.TemporaryDirectory() as raw_directory:
        library = build_library(Path(raw_directory))
        configure(library)
        assert_reborrow_boundary(library)
    print(
        "semantic reborrow: exact local one-statement unique field child, "
        "own-unit flat writer callee, ancestor write attribution, suspension, "
        "non-escape, source anchoring, topology, and deferred sibling fences pass"
    )


if __name__ == "__main__":
    main()
