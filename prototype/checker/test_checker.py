"""Positive/negative tests for the checker-core prototype (D1a gate evidence).

Each negative test asserts BOTH rejection and the exact kernel-spec-v0 rule ID,
matching the DIAG-1 contract (diagnostics cite one rule ID).
"""

import unittest
from checker import (check_fn, CheckError, check_program,
                     RESERVED_BINDING_IDENTS)


def own():
    return {"kind": "own"}


def ref(region, uniq=False):
    return {"kind": "ref", "region": region, "uniq": uniq}


def place(base, *path):
    return {"base": base, "path": list(path)}


def fn(body, params=None, regions=None):
    return {"kind": "fn", "name": "t", "params": params or [],
            "regions": regions or [], "body": body}


class Negative(unittest.TestCase):
    def expect(self, rule, f):
        with self.assertRaises(CheckError) as cm:
            check_fn(f)
        self.assertEqual(cm.exception.rule, rule, str(cm.exception))

    def test_use_after_move(self):
        self.expect("OWN-1", fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "let", "name": "y", "mode": own(),
             "init": {"kind": "move", "place": place("x")}},
            {"kind": "expr", "expr": {"kind": "use", "place": place("x")}},
        ]))

    def test_match_move_copy_rejected_in_flow_layer(self):
        self.expect("OWN-1", fn([
            {"kind": "match",
             "scrut": {"kind": "move", "place": place("x")},
             "arms": [{"binders": [], "body": []}]},
        ], params=[{"name": "x", "mode": own(),
                    "ty": {"kind": "prim", "name": "i32"}}]))

    def test_index_atom_move_copy_rejected_in_flow_layer(self):
        u8 = {"kind": "prim", "name": "u8"}
        u64 = {"kind": "prim", "name": "u64"}
        indexed = {"kind": "index",
                   "place": {"kind": "var", "name": "items"},
                   "elem": u8,
                   "atom": {"kind": "move",
                            "place": {"kind": "var", "name": "offset"}}}
        self.expect("OWN-1", fn([
            {"kind": "expr", "expr": {"kind": "use", "place": indexed}},
        ], params=[
            {"name": "items", "mode": own(),
             "ty": {"kind": "buffer", "elem": u8}},
            {"name": "offset", "mode": own(), "ty": u64},
        ]))

    def test_match_direct_borrow_expression_rejected_before_arm_cleanup(self):
        # The second arm statement pins the former holder=None cleanup bypass:
        # a direct borrow is never a legal match value, even if one arm statement
        # would otherwise prune its temporary borrow.
        self.expect("TYPE-7", fn([
            {"kind": "region", "name": "r", "body": [
                {"kind": "let", "name": "state", "mode": own(),
                 "ty": {"kind": "named", "name": "State"},
                 "init": {"kind": "lit"}},
                {"kind": "match",
                 "scrut": {"kind": "borrow", "region": "r", "uniq": False,
                           "place": {"kind": "var", "name": "state"}},
                 "arms": [{"binders": [], "body": [
                     {"kind": "doc"},
                     {"kind": "set", "place": {"kind": "var", "name": "state"},
                      "expr": {"kind": "lit"}},
                 ]}]},
            ]},
        ]))

    def test_return_affine_through_shared_borrow_rejected_in_flow_layer(self):
        pair = {"kind": "named", "name": "Pair"}
        self.expect("OWN-1", fn([
            {"kind": "return", "expr": {"kind": "use", "place": {
                "kind": "deref", "place": {"kind": "var", "name": "holder"}}}},
        ], params=[{"name": "holder", "mode": ref("r0"), "ty": pair}],
           regions=["r0"]))

    def test_double_mutable_borrow(self):
        self.expect("OWN-5", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},
                {"kind": "let", "name": "q", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},
            ]},
        ]))

    def test_shared_then_mutable_overlap(self):
        self.expect("OWN-5", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x", "f")}},
                {"kind": "let", "name": "q", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},          # overlaps x.f [OWN-7]
            ]},
        ]))

    def test_move_while_borrowed(self):
        self.expect("OWN-5", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x")}},
                {"kind": "let", "name": "y", "mode": own(),
                 "init": {"kind": "move", "place": place("x")}},
            ]},
        ]))

    def test_escape_inner_region_to_outer(self):
        self.expect("OWN-4", fn([
            {"kind": "region", "name": "outer", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "region", "name": "inner", "body": [
                    {"kind": "let", "name": "p", "mode": ref("outer"),
                     "init": {"kind": "borrow", "region": "inner", "uniq": False,
                              "place": place("x")}},     # inner does not outlive outer
                ]},
            ]},
        ]))

    def test_return_local_region_borrow(self):
        self.expect("OWN-4", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "return",
                 "expr": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x")}},
            ]},
        ]))

    def test_write_through_shared_borrow(self):
        self.expect("OWN-5", fn([
            {"kind": "set", "place": place("p"), "expr": {"kind": "lit"}},
        ], params=[{"name": "p", "mode": ref("r0", False)}], regions=["r0"]))

    def test_read_while_mutably_borrowed(self):
        self.expect("OWN-5", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},
                {"kind": "expr", "expr": {"kind": "use", "place": place("x")}},
            ]},
        ]))

    def test_move_through_borrow_binding(self):
        self.expect("OWN-1", fn([
            {"kind": "let", "name": "y", "mode": own(),
             "init": {"kind": "move", "place": place("p")}},
        ], params=[{"name": "p", "mode": ref("r0", True)}], regions=["r0"]))

    def test_dangling_return_of_own_param(self):
        # the critique's counterexample: fn f(x: own T) ['r0] { return &r0 x; }
        self.expect("OWN-10", fn([
            {"kind": "return",
             "expr": {"kind": "borrow", "region": "r0", "uniq": False,
                      "place": place("x")}},
        ], params=[{"name": "x", "mode": own()}], regions=["r0"]))

    def test_dangling_local_into_caller_region(self):
        self.expect("OWN-10", fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "expr",
             "expr": {"kind": "borrow", "region": "r0", "uniq": False,
                      "place": place("x")}},
        ], regions=["r0"]))

    def test_holder_rooted_alias_of_mut_borrow(self):
        # let p = &mut 'a x; &'a p.f resolves to x.f overlapping the &mut of x
        self.expect("OWN-5", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},
                {"kind": "let", "name": "q", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("p", "f")}},
            ]},
        ]))

    def test_loop_borrow_of_outer_region(self):
        self.expect("OWN-11", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "loop", "label": "l", "body": [
                    {"kind": "expr",
                     "expr": {"kind": "borrow", "region": "a", "uniq": False,
                              "place": place("x")}},
                ]},
            ]},
        ]))

    def test_loop_move_of_outer_binding(self):
        self.expect("OWN-11", fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "loop", "label": "l", "body": [
                {"kind": "let", "name": "y", "mode": own(),
                 "init": {"kind": "move", "place": place("x")}},
            ]},
        ]))

    def test_call_two_uniq_args_alias(self):
        self.expect("OWN-12", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "expr", "expr": {"kind": "call", "args": [
                    {"kind": "borrow", "region": "a", "uniq": True, "place": place("x")},
                    {"kind": "borrow", "region": "a", "uniq": True, "place": place("x")},
                ]}},
            ]},
        ]))

    def test_call_shared_plus_uniq_overlap(self):
        self.expect("OWN-12", fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "expr", "expr": {"kind": "call", "args": [
                    {"kind": "borrow", "region": "a", "uniq": False, "place": place("x", "f")},
                    {"kind": "borrow", "region": "a", "uniq": True, "place": place("x")},
                ]}},
            ]},
        ]))

    def test_unknown_region(self):
        self.expect("OWN-3", fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "expr",
             "expr": {"kind": "borrow", "region": "nowhere", "uniq": False,
                      "place": place("x")}},
        ]))


class Positive(unittest.TestCase):
    def ok(self, f):
        self.assertIsNone(check_fn(f))

    def test_sequential_disjoint_borrows_after_region_end(self):
        self.ok(fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "p", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},
                {"kind": "set", "place": place("p"), "expr": {"kind": "lit"}},
            ]},
            {"kind": "region", "name": "b", "body": [
                {"kind": "let", "name": "q", "mode": ref("b", True),
                 "init": {"kind": "borrow", "region": "b", "uniq": True,
                          "place": place("x")}},
            ]},
        ]))

    def test_disjoint_field_borrows(self):
        self.ok(fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x", "f")}},
                {"kind": "let", "name": "q", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x", "g")}},   # f and g disjoint [OWN-7]
            ]},
        ]))

    def test_two_shared_borrows_same_place(self):
        self.ok(fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x")}},
                {"kind": "let", "name": "q", "mode": ref("a"),
                 "init": {"kind": "borrow", "region": "a", "uniq": False,
                          "place": place("x")}},
                {"kind": "expr", "expr": {"kind": "use", "place": place("x")}},
            ]},
        ]))

    def test_return_reborrow_of_caller_borrow(self):
        # sound: re-borrowing through a caller-region borrow into the same region
        self.ok(fn([
            {"kind": "return",
             "expr": {"kind": "borrow", "region": "r0", "uniq": False,
                      "place": place("p")}},
        ], params=[{"name": "p", "mode": ref("r0", False)}], regions=["r0"]))

    def test_write_through_mut_borrow_holder(self):
        self.ok(fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "let", "name": "p", "mode": ref("a", True),
                 "init": {"kind": "borrow", "region": "a", "uniq": True,
                          "place": place("x")}},
                {"kind": "set", "place": place("p"), "expr": {"kind": "lit"}},
            ]},
        ]))

    def test_loop_region_per_iteration_ok(self):
        self.ok(fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "loop", "label": "l", "body": [
                {"kind": "region", "name": "it", "body": [
                    {"kind": "let", "name": "p", "mode": ref("it", True),
                     "init": {"kind": "borrow", "region": "it", "uniq": True,
                              "place": place("x")}},
                    {"kind": "set", "place": place("p"), "expr": {"kind": "lit"}},
                ]},
            ]},
        ]))

    def test_call_two_shared_args_ok(self):
        self.ok(fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "expr", "expr": {"kind": "call", "args": [
                    {"kind": "borrow", "region": "a", "uniq": False, "place": place("x")},
                    {"kind": "borrow", "region": "a", "uniq": False, "place": place("x")},
                ]}},
            ]},
        ]))

    def test_call_disjoint_uniq_fields_ok(self):
        self.ok(fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "expr", "expr": {"kind": "call", "args": [
                    {"kind": "borrow", "region": "a", "uniq": True, "place": place("x", "f")},
                    {"kind": "borrow", "region": "a", "uniq": True, "place": place("x", "g")},
                ]}},
            ]},
        ]))

    def test_match_own_scrutinee_moves(self):
        with self.assertRaises(CheckError) as cm:
            check_fn(fn([
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "match", "scrut": {"kind": "use", "place": place("x")},
                 "arms": [{"binders": [], "body": []}]},
                {"kind": "expr", "expr": {"kind": "use", "place": place("x")}},
            ]))
        self.assertEqual(cm.exception.rule, "OWN-1")

    def test_match_uniq_binder_conflicts_with_root_borrow(self):
        with self.assertRaises(CheckError) as cm:
            check_fn(fn([
                {"kind": "match", "scrut": {"kind": "use",
                                               "place": deref(var("p"))},
                 "arms": [{"binders": ["v"], "body": [
                     {"kind": "let", "name": "q", "mode": ref("r0", True),
                      "init": {"kind": "borrow", "region": "r0", "uniq": True,
                               "place": place("p")}}]}]},
            ], params=[{"name": "p", "mode": ref("r0", True)}], regions=["r0"]))
        self.assertEqual(cm.exception.rule, "OWN-5")

    def test_match_ref_scrutinee_stays_live(self):
        self.assertIsNone(check_fn(fn([
            {"kind": "match", "scrut": {"kind": "use",
                                           "place": deref(var("p"))},
             "arms": [{"binders": ["v"], "body": [
                 {"kind": "expr", "expr": {"kind": "use",
                                              "place": deref(var("v"))}}]}]},
            {"kind": "expr", "expr": {"kind": "use",
                                          "place": deref(var("p"))}},
        ], params=[{"name": "p", "mode": ref("r0", False)}], regions=["r0"])))

    def test_flow_only_index_atom_affine_move_checked_exactly_once(self):
        # This deliberately bypasses the type layer: AffineOffset is not a legal
        # u64 index offset. The probe isolates one flow traversal of the atom.
        u8 = {"kind": "prim", "name": "u8"}
        indexed = {"kind": "index",
                   "place": {"kind": "var", "name": "items"},
                   "elem": u8,
                   "atom": {"kind": "move",
                            "place": {"kind": "var", "name": "offset"}}}
        self.ok(fn([
            {"kind": "expr", "expr": {"kind": "use", "place": indexed}},
        ], params=[
            {"name": "items", "mode": own(),
             "ty": {"kind": "buffer", "elem": u8}},
            {"name": "offset", "mode": own(),
             "ty": {"kind": "named", "name": "AffineOffset"}},
        ]))

    def test_match_arm_isolation_uniq_in_both_arms(self):
        # sequential approximation used to false-reject this
        self.ok(fn([
            {"kind": "region", "name": "a", "body": [
                {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
                {"kind": "match", "scrut": {"kind": "lit"}, "arms": [
                    {"binders": [], "body": [
                        {"kind": "let", "name": "p", "mode": ref("a", True),
                         "init": {"kind": "borrow", "region": "a", "uniq": True,
                                  "place": place("x")}}]},
                    {"binders": [], "body": [
                        {"kind": "let", "name": "q", "mode": ref("a", True),
                         "init": {"kind": "borrow", "region": "a", "uniq": True,
                                  "place": place("x")}}]},
                ]},
            ]},
        ]))

    def test_match_join_move_in_one_arm(self):
        with self.assertRaises(CheckError) as cm:
            check_fn(fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "match", "scrut": {"kind": "lit"}, "arms": [
                {"binders": [], "body": [
                    {"kind": "let", "name": "y", "mode": own(),
                     "init": {"kind": "move", "place": place("x")}}]},
                {"binders": [], "body": []},
            ]},
            {"kind": "expr", "expr": {"kind": "use", "place": place("x")}},
        ]))
        self.assertEqual(cm.exception.rule, "OWN-1")

    def test_move_then_rebind_fresh(self):
        self.ok(fn([
            {"kind": "let", "name": "x", "mode": own(), "init": {"kind": "lit"}},
            {"kind": "let", "name": "y", "mode": own(),
             "init": {"kind": "move", "place": place("x")}},
            {"kind": "expr", "expr": {"kind": "use", "place": place("y")}},
        ]))


# ---------------------------------------------------------------------------
# v0.6 type-layer tests, driven through check_program (GRAM-8/10/11, TYPE-5/6/7,
# GIVE-1). These exercise the type layer added alongside the ownership checker.
# ---------------------------------------------------------------------------

I32 = {"kind": "prim", "name": "i32"}
U8 = {"kind": "prim", "name": "u8"}
U32 = {"kind": "prim", "name": "u32"}
U64 = {"kind": "prim", "name": "u64"}
UNIT = {"kind": "unit"}


def named(n):
    return {"kind": "named", "name": n}


def var(n):
    return {"kind": "var", "name": n}


def deref(pl):
    return {"kind": "deref", "place": pl}


def field(pl, name):
    return {"kind": "field", "place": pl, "name": name}


def indexed(pl, elem, atom):
    return {"kind": "index", "place": pl, "elem": elem, "atom": atom}


def lit(ty=I32):
    return {"kind": "lit", "ty": ty}


def use(pl):
    return {"kind": "use", "place": pl}


def op(callee, args, tyargs=(I32,)):
    return {"kind": "call", "callee": callee, "args": list(args),
            "argnames": None, "tyargs": list(tyargs)}


def ucall(callee, argnames, args):
    return {"kind": "call", "callee": callee, "args": list(args),
            "argnames": list(argnames)}


def construct(name, fields):
    return {"kind": "construct", "name": name,
            "fields": [{"name": n, "atom": a} for (n, a) in fields]}


def pfn(body, params=None, regions=None, rmode=None, rty=UNIT):
    return {"regions": regions or [], "params": params or [],
            "rmode": rmode or own(), "rty": rty, "body": body}


SIGN = {"Sign": [{"variant": "Neg", "fields": []},
                 {"variant": "Zero", "fields": []},
                 {"variant": "Pos", "fields": []}]}
POINT = {"Point": [{"name": "x", "ty": I32}, {"name": "y", "ty": I32}]}
SIGN_OF = pfn([{"kind": "return", "expr": construct("Pos", [])}],
              params=[{"name": "x", "mode": own(), "ty": I32}],
              rmode=own(), rty=named("Sign"))


def value_match(name, ty, arms, mode=None):
    return {"kind": "let", "name": name, "mode": mode or own(), "ty": ty,
            "init": {"kind": "match",
                     "scrut": op("iadd.checked", [lit(), lit()]),
                     "arms": arms}}


class ProgramLayer(unittest.TestCase):
    def expect(self, rule, prog):
        with self.assertRaises(CheckError) as cm:
            check_program(prog)
        self.assertEqual(cm.exception.rule, rule, str(cm.exception))

    def ok(self, prog):
        self.assertIsNone(check_program(prog))

    def test_full_program_accepts(self):
        main = pfn([
            {"kind": "let", "name": "a", "mode": own(), "ty": I32, "init": lit()},
            {"kind": "region", "name": "r", "body": [
                {"kind": "let", "name": "p", "mode": ref("r"), "ty": I32,
                 "init": {"kind": "borrow", "region": "r", "uniq": False,
                          "place": var("a")}},
                value_match("v", I32, [
                    {"variant": "Ok", "binders": [{"field": "value", "name": "w"}],
                     "body": [{"kind": "give", "expr": use(var("w"))}]},
                    {"variant": "Err", "binders": [{"field": "error", "name": "e"}],
                     "body": [{"kind": "return", "expr": lit(UNIT)}]},
                ]),
                {"kind": "check", "expr": op("ieq", [use(var("v")), lit()])},
                {"kind": "let", "name": "sg", "mode": own(), "ty": named("Sign"),
                 "init": ucall("sign_of", ["x"], [use(var("v"))])},
                {"kind": "let", "name": "pt", "mode": own(), "ty": named("Point"),
                 "init": construct("Point", [("x", lit()), ("y", lit())])},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], rmode=own(), rty=UNIT)
        self.ok({"structs": POINT, "enums": SIGN,
                 "fns": {"sign_of": SIGN_OF, "main": main}})

    def test_form3_every_op1_reserved_identifier_rejected(self):
        for name in sorted(RESERVED_BINDING_IDENTS):
            with self.subTest(name=name):
                self.expect("FORM-3", {"structs": {}, "enums": {},
                            "fns": {name: pfn([
                                {"kind": "return", "expr": lit(UNIT)}
                            ])}})

    def test_form3_reservation_covers_every_binding_shape(self):
        return_unit = {"kind": "return", "expr": lit(UNIT)}
        cases = {
            "struct field": {
                "structs": {"S": [{"name": "trap", "ty": I32}]},
                "enums": {}, "fns": {},
            },
            "variant field": {
                "structs": {},
                "enums": {"E": [{"variant": "V", "fields": [
                    {"name": "trap", "ty": I32}
                ]}]},
                "fns": {},
            },
            "parameter": {
                "structs": {}, "enums": {},
                "fns": {"f": pfn([return_unit], params=[
                    {"name": "trap", "mode": own(), "ty": I32}
                ])},
            },
            "region parameter": {
                "structs": {}, "enums": {},
                "fns": {"f": pfn([return_unit], regions=["trap"])},
            },
            "let binder": {
                "structs": {}, "enums": {},
                "fns": {"f": pfn([
                    {"kind": "let", "name": "trap", "mode": own(),
                     "ty": I32, "init": lit()},
                    return_unit,
                ])},
            },
            "try binder": {
                "structs": {}, "enums": {},
                "fns": {"f": pfn([
                    {"kind": "try", "name": "trap", "mode": own(),
                     "ty": I32, "expr": lit()},
                    return_unit,
                ])},
            },
            "match binder": {
                "structs": {}, "enums": {},
                "fns": {"f": pfn([
                    {"kind": "match", "arms": [{
                        "variant": "Ok",
                        "binders": [{"field": "value", "name": "trap"}],
                        "body": [],
                    }]},
                    return_unit,
                ])},
            },
            "local region": {
                "structs": {}, "enums": {},
                "fns": {"f": pfn([
                    {"kind": "region", "name": "trap", "body": []},
                    return_unit,
                ])},
            },
            "const": {
                "structs": {}, "enums": {}, "fns": {},
                "consts": {"trap": I32},
            },
        }
        for shape, prog in cases.items():
            with self.subTest(shape=shape):
                self.expect("FORM-3", prog)

    def test_gram8_wrong_field_name(self):
        self.expect("GRAM-8", {"structs": POINT, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": construct("Point", [("x", lit()), ("z", lit())])}],
            rmode=own(), rty=named("Point"))}})

    def test_gram8_out_of_order(self):
        self.expect("GRAM-8", {"structs": POINT, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": construct("Point", [("y", lit()), ("x", lit())])}],
            rmode=own(), rty=named("Point"))}})

    def test_gram8_arity(self):
        self.expect("GRAM-8", {"structs": POINT, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": construct("Point", [("x", lit())])}],
            rmode=own(), rty=named("Point"))}})

    def test_gram10_wrong_binder_field(self):
        self.expect("GRAM-10", {"structs": {}, "enums": {}, "fns": {"g": pfn([
            value_match("v", I32, [
                {"variant": "Ok", "binders": [{"field": "wrong", "name": "w"}],
                 "body": [{"kind": "give", "expr": use(var("w"))}]},
                {"variant": "Err", "binders": [{"field": "error", "name": "e"}],
                 "body": [{"kind": "return", "expr": lit(UNIT)}]},
            ]),
            {"kind": "return", "expr": lit(UNIT)}])}})

    def test_gram10_binder_not_fresh(self):
        self.expect("GRAM-10", {"structs": {}, "enums": {}, "fns": {"g": pfn([
            {"kind": "let", "name": "w", "mode": own(), "ty": I32, "init": lit()},
            value_match("v", I32, [
                {"variant": "Ok", "binders": [{"field": "value", "name": "w"}],
                 "body": [{"kind": "give", "expr": use(var("w"))}]},
                {"variant": "Err", "binders": [{"field": "error", "name": "e"}],
                 "body": [{"kind": "return", "expr": lit(UNIT)}]},
            ]),
            {"kind": "return", "expr": lit(UNIT)}])}})

    def test_gram11_user_call_unnamed(self):
        self.expect("GRAM-11", {"structs": {}, "enums": SIGN,
                    "fns": {"sign_of": SIGN_OF, "g": pfn(
            [{"kind": "return", "expr":
              {"kind": "call", "callee": "sign_of", "args": [lit()], "argnames": None}}],
            rmode=own(), rty=named("Sign"))}})

    def test_gram11_user_call_wrong_name(self):
        self.expect("GRAM-11", {"structs": {}, "enums": SIGN,
                    "fns": {"sign_of": SIGN_OF, "g": pfn(
            [{"kind": "return", "expr": ucall("sign_of", ["y"], [lit()])}],
            rmode=own(), rty=named("Sign"))}})

    def test_gram11_table_op_named(self):
        self.expect("GRAM-11", {"structs": {}, "enums": {}, "fns": {"g": pfn(
            [{"kind": "return", "expr":
              {"kind": "call", "callee": "iadd.wrap", "args": [lit(), lit()],
               "argnames": ["a", "b"], "tyargs": [I32]}}], rmode=own(), rty=I32)}})

    def test_op6_total_cvt_returns_destination_type(self):
        i8 = {"kind": "prim", "name": "i8"}
        main = pfn([
            {"kind": "let", "name": "wide", "mode": own(), "ty": I32,
             "init": op("cvt", [lit(i8)], tyargs=[i8, I32])},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": {}, "enums": {}, "fns": {"main": main}})

    def test_op6_checked_cvt_returns_specialized_result(self):
        i8 = {"kind": "prim", "name": "i8"}
        main = pfn([
            {"kind": "match",
             "scrut": op("cvt", [lit(I32)], tyargs=[I32, i8]),
             "arms": [
                 {"variant": "Ok",
                  "binders": [{"field": "value", "name": "value"}],
                  "body": [{"kind": "let", "name": "saved", "mode": own(),
                            "ty": i8, "init": use(var("value"))}]},
                 {"variant": "Err",
                  "binders": [{"field": "error", "name": "error"}],
                  "body": [{"kind": "match", "scrut": use(var("error")),
                            "arms": [{"variant": "NarrowError", "binders": [],
                                      "body": []}]}]},
             ]},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": {}, "enums": {}, "fns": {"main": main}})

    def test_op6_same_type_cvt_is_not_an_operation(self):
        main = pfn([
            {"kind": "let", "name": "same", "mode": own(), "ty": I32,
             "init": op("cvt", [lit()], tyargs=[I32, I32])},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.expect("OP-6", {"structs": {}, "enums": {},
                             "fns": {"main": main}})

    def test_own1_bare_affine_call_arg_rejected(self):
        buf = {"kind": "buffer", "elem": {"kind": "prim", "name": "u8"}}
        consume = pfn([{"kind": "return", "expr": lit(UNIT)}],
                      params=[{"name": "b", "mode": own(), "ty": buf}])
        caller = pfn([
            {"kind": "expr", "expr": ucall("consume", ["b"], [use(var("src"))])},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "src", "mode": own(), "ty": buf}])
        self.expect("OWN-1", {"structs": {}, "enums": {},
                              "fns": {"consume": consume, "caller": caller}})

    def test_own1_explicit_affine_call_arg_moves(self):
        buf = {"kind": "buffer", "elem": {"kind": "prim", "name": "u8"}}
        consume = pfn([{"kind": "return", "expr": lit(UNIT)}],
                      params=[{"name": "b", "mode": own(), "ty": buf}])
        caller = pfn([
            {"kind": "expr", "expr": ucall("consume", ["b"], [
                {"kind": "move", "place": var("src")}
            ])},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "src", "mode": own(), "ty": buf}])
        self.ok({"structs": {}, "enums": {},
                 "fns": {"consume": consume, "caller": caller}})

    def test_own1_match_move_tag_only_copy_rejected(self):
        states = {"State": [{"variant": "Ready", "fields": []},
                            {"variant": "Done", "fields": []}]}
        main = pfn([
            {"kind": "let", "name": "state", "mode": own(),
             "ty": named("State"), "init": construct("Ready", [])},
            {"kind": "match",
             "scrut": {"kind": "move", "place": var("state")},
             "arms": [
                 {"variant": "Ready", "binders": [], "body": []},
                 {"variant": "Done", "binders": [], "body": []},
             ]},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.expect("OWN-1", {"structs": {}, "enums": states,
                              "fns": {"main": main}})

    def test_own1_index_atom_move_copy_rejected(self):
        buf = {"kind": "buffer", "elem": U8}
        main = pfn([
            {"kind": "let", "name": "value", "mode": own(), "ty": U8,
             "init": use(indexed(var("items"), U8,
                                 {"kind": "move", "place": var("offset")}))},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[
            {"name": "items", "mode": own(), "ty": buf},
            {"name": "offset", "mode": own(), "ty": U64},
        ])
        self.expect("OWN-1", {"structs": {}, "enums": {},
                              "fns": {"main": main}})

    def test_type5_index_offset_must_be_u64(self):
        buf = {"kind": "buffer", "elem": U8}
        main = pfn([
            {"kind": "let", "name": "value", "mode": own(), "ty": U8,
             "init": use(indexed(var("items"), U8, lit(U32)))},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "items", "mode": own(), "ty": buf}])
        self.expect("TYPE-5", {"structs": {}, "enums": {},
                               "fns": {"main": main}})

    def test_type7_match_reference_holder_requires_deref(self):
        states = {"State": [{"variant": "Ready", "fields": []},
                            {"variant": "Done", "fields": []}]}
        main = pfn([
            {"kind": "match", "scrut": use(var("state")), "arms": [
                {"variant": "Ready", "binders": [], "body": []},
                {"variant": "Done", "binders": [], "body": []},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "state", "mode": ref("r0"),
                    "ty": named("State")}], regions=["r0"])
        self.expect("TYPE-7", {"structs": {}, "enums": states,
                               "fns": {"main": main}})

    def test_type7_index_reference_holder_requires_deref(self):
        buf = {"kind": "buffer", "elem": U8}
        main = pfn([
            {"kind": "let", "name": "value", "mode": own(), "ty": U8,
             "init": use(indexed(var("items"), U8, lit(U64)))},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "items", "mode": ref("r0"), "ty": buf}],
           regions=["r0"])
        self.expect("TYPE-7", {"structs": {}, "enums": {},
                               "fns": {"main": main}})

    def test_type7_index_explicit_deref_accepts(self):
        buf = {"kind": "buffer", "elem": U8}
        main = pfn([
            {"kind": "let", "name": "value", "mode": own(), "ty": U8,
             "init": use(indexed(deref(var("items")), U8, lit(U64)))},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "items", "mode": ref("r0"), "ty": buf}],
           regions=["r0"])
        self.ok({"structs": {}, "enums": {}, "fns": {"main": main}})

    def test_own1_bare_match_copy_remains_live(self):
        states = {"State": [{"variant": "Ready", "fields": []},
                            {"variant": "Done", "fields": []}]}
        arms = [
            {"variant": "Ready", "binders": [], "body": []},
            {"variant": "Done", "binders": [], "body": []},
        ]
        main = pfn([
            {"kind": "let", "name": "state", "mode": own(),
             "ty": named("State"), "init": construct("Ready", [])},
            {"kind": "match", "scrut": use(var("state")), "arms": arms},
            {"kind": "match", "scrut": use(var("state")), "arms": arms},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": {}, "enums": states, "fns": {"main": main}})

    def test_own1_bare_match_projected_copy_field_preserves_root(self):
        states = {"State": [{"variant": "Ready", "fields": []},
                            {"variant": "Done", "fields": []}]}
        holder = {"Holder": [{"name": "state", "ty": named("State")}]}
        arms = [
            {"variant": "Ready", "binders": [], "body": []},
            {"variant": "Done", "binders": [], "body": []},
        ]
        main = pfn([
            {"kind": "let", "name": "state", "mode": own(),
             "ty": named("State"), "init": construct("Ready", [])},
            {"kind": "let", "name": "holder", "mode": own(),
             "ty": named("Holder"),
             "init": construct("Holder", [("state", use(var("state")))])},
            {"kind": "match", "scrut": use(field(var("holder"), "state")),
             "arms": arms},
            {"kind": "match", "scrut": use(field(var("holder"), "state")),
             "arms": arms},
            {"kind": "let", "name": "saved", "mode": own(),
             "ty": named("Holder"),
             "init": {"kind": "move", "place": var("holder")}},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": holder, "enums": states, "fns": {"main": main}})

    def test_own1_bare_match_projected_copy_element_preserves_buffer(self):
        bool_ty = named("Bool")
        buf = {"kind": "buffer", "elem": bool_ty}
        arms = [
            {"variant": "True", "binders": [], "body": []},
            {"variant": "False", "binders": [], "body": []},
        ]
        main = pfn([
            {"kind": "match",
             "scrut": use(indexed(var("items"), bool_ty, lit(U64))),
             "arms": arms},
            {"kind": "match",
             "scrut": use(indexed(var("items"), bool_ty, lit(U64))),
             "arms": arms},
            {"kind": "let", "name": "saved", "mode": own(), "ty": buf,
             "init": {"kind": "move", "place": var("items")}},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "items", "mode": own(), "ty": buf}])
        self.ok({"structs": {}, "enums": {}, "fns": {"main": main}})

    def test_own13_bare_match_affine_consumes(self):
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "value", "ty": I32}
        ]}]}
        main = pfn([
            {"kind": "let", "name": "packet", "mode": own(),
             "ty": named("Packet"),
             "init": construct("Data", [("value", lit())])},
            {"kind": "match", "scrut": use(var("packet")), "arms": [
                {"variant": "Data",
                 "binders": [{"field": "value", "name": "value"}],
                 "body": []},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": {}, "enums": packets, "fns": {"main": main}})

    def test_own13_explicit_match_affine_remains_legal(self):
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "value", "ty": I32}
        ]}]}
        main = pfn([
            {"kind": "let", "name": "packet", "mode": own(),
             "ty": named("Packet"),
             "init": construct("Data", [("value", lit())])},
            {"kind": "match",
             "scrut": {"kind": "move", "place": var("packet")},
             "arms": [
                 {"variant": "Data",
                  "binders": [{"field": "value", "name": "value"}],
                  "body": []},
             ]},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": {}, "enums": packets, "fns": {"main": main}})

    def test_type7_direct_borrow_expression_match_rejected(self):
        states = {"State": [{"variant": "Ready", "fields": []}]}
        main = pfn([
            {"kind": "region", "name": "r", "body": [
                {"kind": "match",
                 "scrut": {"kind": "borrow", "region": "r", "uniq": False,
                           "place": var("state")},
                 "arms": [{"variant": "Ready", "binders": [], "body": [
                     {"kind": "doc"},
                     {"kind": "set", "place": var("state"),
                      "expr": construct("Ready", [])},
                 ]}]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "state", "mode": own(), "ty": named("State")}])
        self.expect("TYPE-7", {"structs": {}, "enums": states,
                               "fns": {"main": main}})

    def test_type7_ref_returning_call_cannot_be_matched_directly(self):
        states = {"State": [{"variant": "Ready", "fields": []}]}
        get = pfn([{"kind": "return", "expr": use(var("state"))}],
                  params=[{"name": "state", "mode": ref("r0"),
                           "ty": named("State")}], regions=["r0"],
                  rmode=ref("r0"), rty=named("State"))
        main = pfn([
            {"kind": "match",
             "scrut": ucall("get", ["state"], [use(var("state"))]),
             "arms": [{"variant": "Ready", "binders": [], "body": []}]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "state", "mode": ref("r0"),
                    "ty": named("State")}], regions=["r0"])
        self.expect("TYPE-7", {"structs": {}, "enums": states,
                               "fns": {"get": get, "main": main}})

    def test_type7_match_box_and_arena_holders_require_deref(self):
        states = {"State": [{"variant": "Ready", "fields": []}]}
        holders = [
            {"kind": "box", "elem": named("State")},
            {"kind": "arena", "region": "r0", "elem": named("State")},
        ]
        for holder_ty in holders:
            with self.subTest(holder=holder_ty["kind"]):
                main = pfn([
                    {"kind": "match", "scrut": use(var("holder")),
                     "arms": [{"variant": "Ready", "binders": [], "body": []}]},
                    {"kind": "return", "expr": lit(UNIT)},
                ], params=[{"name": "holder", "mode": own(), "ty": holder_ty}],
                   regions=["r0"])
                self.expect("TYPE-7", {"structs": {}, "enums": states,
                                       "fns": {"main": main}})

    def test_type5_match_requires_enum_scrutinee(self):
        main = pfn([
            {"kind": "match", "scrut": use(var("value")),
             "arms": [{"variant": "True", "binders": [], "body": []}]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "value", "mode": own(), "ty": I32}])
        self.expect("TYPE-5", {"structs": {}, "enums": {},
                               "fns": {"main": main}})

    def test_type5_index_stated_element_must_match_container(self):
        buf = {"kind": "buffer", "elem": U8}
        main = pfn([
            {"kind": "let", "name": "value", "mode": own(), "ty": U32,
             "init": use(indexed(var("items"), U32, lit(U64)))},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "items", "mode": own(), "ty": buf}])
        self.expect("TYPE-5", {"structs": {}, "enums": {},
                               "fns": {"main": main}})

    def test_type7_index_box_and_arena_holders_require_deref(self):
        buf = {"kind": "buffer", "elem": U8}
        holders = [
            {"kind": "box", "elem": buf},
            {"kind": "arena", "region": "r0", "elem": buf},
        ]
        for holder_ty in holders:
            with self.subTest(holder=holder_ty["kind"]):
                main = pfn([
                    {"kind": "let", "name": "value", "mode": own(), "ty": U8,
                     "init": use(indexed(var("holder"), U8, lit(U64)))},
                    {"kind": "return", "expr": lit(UNIT)},
                ], params=[{"name": "holder", "mode": own(), "ty": holder_ty}],
                   regions=["r0"])
                self.expect("TYPE-7", {"structs": {}, "enums": {},
                                       "fns": {"main": main}})

    def test_type7_try_holders_require_deref(self):
        error = named("Overflow")
        result = {"kind": "named", "name": "Result", "args": [I32, error]}
        holders = [
            (ref("r0"), result),
            (own(), {"kind": "box", "elem": result}),
            (own(), {"kind": "arena", "region": "r0", "elem": result}),
        ]
        for mode, holder_ty in holders:
            with self.subTest(holder=holder_ty.get("kind")):
                main = pfn([
                    {"kind": "try", "name": "value", "mode": own(),
                     "ty": I32, "expr": use(var("holder"))},
                    {"kind": "return", "expr": construct(
                        "Ok", [("value", lit(UNIT))])},
                ], params=[{"name": "holder", "mode": mode, "ty": holder_ty}],
                   regions=["r0"], rty={"kind": "named", "name": "Result",
                                            "args": [UNIT, error]})
                self.expect("TYPE-7", {"structs": {}, "enums": {},
                                       "fns": {"main": main}})

    def test_type7_return_holders_require_deref_for_referent(self):
        holders = [
            (ref("r0"), I32),
            (own(), {"kind": "box", "elem": I32}),
            (own(), {"kind": "arena", "region": "r0", "elem": I32}),
        ]
        for mode, holder_ty in holders:
            with self.subTest(holder=holder_ty.get("kind")):
                main = pfn([{"kind": "return", "expr": use(var("holder"))}],
                           params=[{"name": "holder", "mode": mode,
                                    "ty": holder_ty}], regions=["r0"], rty=I32)
                self.expect("TYPE-7", {"structs": {}, "enums": {},
                                       "fns": {"main": main}})

    def test_own1_contextual_return_moves_affine_place(self):
        pair = {"Pair": [{"name": "left", "ty": I32}]}
        return_pair = pfn([
            {"kind": "return", "expr": use(var("item"))},
        ], params=[{"name": "item", "mode": own(), "ty": named("Pair")}],
           rty=named("Pair"))
        self.ok({"structs": pair, "enums": {}, "fns": {"return_pair": return_pair}})

        use_after_return = pfn([
            {"kind": "return", "expr": use(var("item"))},
            {"kind": "return", "expr": use(var("item"))},
        ], params=[{"name": "item", "mode": own(), "ty": named("Pair")}],
           rty=named("Pair"))
        self.expect("OWN-1", {"structs": pair, "enums": {},
                              "fns": {"use_after_return": use_after_return}})

    def test_own1_contextual_return_box_and_borrowed_box(self):
        states = {"State": [{"variant": "Ready", "fields": []}]}
        box_state = {"kind": "box", "elem": named("State")}
        owned = pfn([{"kind": "return", "expr": use(var("holder"))}],
                    params=[{"name": "holder", "mode": own(), "ty": box_state}],
                    rty=box_state)
        self.ok({"structs": {}, "enums": states, "fns": {"owned": owned}})

        borrowed = pfn([
            {"kind": "return", "expr": use(deref(var("holder")))},
        ], params=[{"name": "holder", "mode": ref("r0"), "ty": box_state}],
           regions=["r0"], rty=box_state)
        self.expect("OWN-1", {"structs": {}, "enums": states,
                              "fns": {"borrowed": borrowed}})

    def test_const2_contextual_return_copies_indexed_const_element(self):
        table_ty = {"kind": "array", "elem": U8, "n": 4}
        read = pfn([
            {"kind": "return",
             "expr": use(indexed(var("table"), U8, lit(U64)))},
        ], rty=U8)
        self.ok({"structs": {}, "enums": {}, "consts": {"table": table_ty},
                 "fns": {"read": read}})

    def test_own13_shared_match_preserves_affine_payload_provenance(self):
        pair = {"Pair": [{"name": "left", "ty": I32}]}
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "item", "ty": named("Pair")}
        ]}]}
        main = pfn([
            {"kind": "match", "scrut": use(deref(var("packet"))), "arms": [
                {"variant": "Data",
                 "binders": [{"field": "item", "name": "item"}],
                 "body": [
                     {"kind": "let", "name": "left", "mode": own(), "ty": I32,
                      "init": use(field(deref(var("item")), "left"))},
                 ]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "packet", "mode": ref("r0"),
                    "ty": named("Packet")}], regions=["r0"])
        self.ok({"structs": pair, "enums": packets, "fns": {"main": main}})

    def test_own1_match_move_through_borrow_rejected_before_arm_typing(self):
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "value", "ty": I32}
        ]}]}
        main = pfn([
            {"kind": "match",
             "scrut": {"kind": "move", "place": deref(var("packet"))},
             "arms": [{"variant": "Data",
                       "binders": [{"field": "value", "name": "value"}],
                       "body": [{"kind": "let", "name": "saved",
                                 "mode": own(), "ty": I32,
                                 "init": use(deref(var("value")))}]}]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "packet", "mode": ref("r0"),
                    "ty": named("Packet")}], regions=["r0"])
        self.expect("OWN-1", {"structs": {}, "enums": packets,
                              "fns": {"main": main}})

    def test_own5_shared_match_cannot_move_affine_payload(self):
        pair = {"Pair": [{"name": "left", "ty": I32}]}
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "item", "ty": named("Pair")}
        ]}]}
        main = pfn([
            {"kind": "match", "scrut": use(deref(var("packet"))), "arms": [
                {"variant": "Data",
                 "binders": [{"field": "item", "name": "item"}],
                 "body": [{"kind": "let", "name": "stolen", "mode": own(),
                           "ty": named("Pair"),
                           "init": {"kind": "move", "place": deref(var("item"))}}]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "packet", "mode": ref("r0"),
                    "ty": named("Packet")}], regions=["r0"])
        self.expect("OWN-5", {"structs": pair, "enums": packets,
                              "fns": {"main": main}})

    def test_own13_uniq_match_projects_disjoint_payload_borrows(self):
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "left", "ty": I32}, {"name": "right", "ty": I32}
        ]}]}
        main = pfn([
            {"kind": "let", "name": "packet", "mode": own(),
             "ty": named("Packet"),
             "init": construct("Data", [("left", lit()), ("right", lit())])},
            {"kind": "region", "name": "r", "body": [
                {"kind": "let", "name": "holder", "mode": ref("r", True),
                 "ty": named("Packet"),
                 "init": {"kind": "borrow", "region": "r", "uniq": True,
                          "place": var("packet")}},
                {"kind": "match", "scrut": use(deref(var("holder"))), "arms": [
                    {"variant": "Data", "binders": [
                        {"field": "left", "name": "left"},
                        {"field": "right", "name": "right"},
                     ], "body": [
                         {"kind": "let", "name": "saved", "mode": own(),
                          "ty": I32, "init": use(deref(var("left")))},
                         {"kind": "set", "place": deref(var("right")),
                          "expr": lit()},
                     ]},
                ]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ])
        self.ok({"structs": {}, "enums": packets, "fns": {"main": main}})

    def test_own5_uniq_match_freezes_parent_holder_inside_arm(self):
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "left", "ty": I32}
        ]}]}
        main = pfn([
            {"kind": "match", "scrut": use(deref(var("packet"))), "arms": [
                {"variant": "Data",
                 "binders": [{"field": "left", "name": "left"}],
                 "body": [{"kind": "match",
                           "scrut": use(deref(var("packet"))),
                           "arms": [{"variant": "Data",
                                     "binders": [{"field": "left",
                                                  "name": "nested"}],
                                     "body": []}]}]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "packet", "mode": ref("r0", True),
                    "ty": named("Packet")}], regions=["r0"])
        self.expect("OWN-5", {"structs": {}, "enums": packets,
                              "fns": {"main": main}})

    def test_own1_uniq_match_affine_payload_remains_non_owning(self):
        pair = {"Pair": [{"name": "left", "ty": I32}]}
        packets = {"Packet": [{"variant": "Data", "fields": [
            {"name": "item", "ty": named("Pair")}
        ]}]}
        main = pfn([
            {"kind": "match", "scrut": use(deref(var("packet"))), "arms": [
                {"variant": "Data",
                 "binders": [{"field": "item", "name": "item"}],
                 "body": [{"kind": "let", "name": "stolen", "mode": own(),
                           "ty": named("Pair"),
                           "init": {"kind": "move", "place": deref(var("item"))}}]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "packet", "mode": ref("r0", True),
                    "ty": named("Packet")}], regions=["r0"])
        self.expect("OWN-5", {"structs": pair, "enums": packets,
                              "fns": {"main": main}})

    def test_own1_user_enum_copy_payload_binder_can_be_matched_twice(self):
        states = {"State": [{"variant": "Ready", "fields": []}]}
        wrappers = {"Wrapper": [{"variant": "Wrapped", "fields": [
            {"name": "state", "ty": named("State")}
        ]}]}
        nested = {"kind": "match", "scrut": use(var("state")),
                  "arms": [{"variant": "Ready", "binders": [], "body": []}]}
        main = pfn([
            {"kind": "match", "scrut": use(var("wrapper")), "arms": [
                {"variant": "Wrapped",
                 "binders": [{"field": "state", "name": "state"}],
                 "body": [nested, nested]},
            ]},
            {"kind": "return", "expr": lit(UNIT)},
        ], params=[{"name": "wrapper", "mode": own(),
                    "ty": named("Wrapper")}])
        self.ok({"structs": {}, "enums": {**states, **wrappers},
                 "fns": {"main": main}})

    def test_own1_result_and_option_affine_payload_binders_can_move(self):
        buf = {"kind": "buffer", "elem": U8}
        error = named("Overflow")
        cases = [
            ({"kind": "named", "name": "Result", "args": [buf, error]},
             [{"variant": "Ok",
               "binders": [{"field": "value", "name": "value"}],
               "body": [{"kind": "let", "name": "taken", "mode": own(),
                         "ty": buf,
                         "init": {"kind": "move", "place": var("value")}}]},
              {"variant": "Err",
               "binders": [{"field": "error", "name": "error"}], "body": []}]),
            ({"kind": "named", "name": "Option", "args": [buf]},
             [{"variant": "Some",
               "binders": [{"field": "value", "name": "value"}],
               "body": [{"kind": "let", "name": "taken", "mode": own(),
                         "ty": buf,
                         "init": {"kind": "move", "place": var("value")}}]},
              {"variant": "None", "binders": [], "body": []}]),
        ]
        for payload_ty, arms in cases:
            with self.subTest(container=payload_ty["name"]):
                main = pfn([
                    {"kind": "match", "scrut": use(var("container")), "arms": arms},
                    {"kind": "return", "expr": lit(UNIT)},
                ], params=[{"name": "container", "mode": own(), "ty": payload_ty}])
                self.ok({"structs": {}, "enums": {}, "fns": {"main": main}})

    def test_own1_try_copy_payload_binder_can_be_matched_twice(self):
        states = {"State": [{"variant": "Ready", "fields": []}]}
        error = named("Overflow")
        incoming = {"kind": "named", "name": "Result",
                    "args": [named("State"), error]}
        outgoing = {"kind": "named", "name": "Result", "args": [UNIT, error]}
        nested = {"kind": "match", "scrut": use(var("state")),
                  "arms": [{"variant": "Ready", "binders": [], "body": []}]}
        main = pfn([
            {"kind": "try", "name": "state", "mode": own(),
             "ty": named("State"), "expr": use(var("incoming"))},
            nested,
            nested,
            {"kind": "return", "expr": construct("Ok", [("value", lit(UNIT))])},
        ], params=[{"name": "incoming", "mode": own(), "ty": incoming}],
           rty=outgoing)
        self.ok({"structs": {}, "enums": states, "fns": {"main": main}})

    def test_type7_borrow_as_value(self):
        self.expect("TYPE-7", {"structs": {}, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": use(var("p"))}],
            params=[{"name": "p", "mode": ref("r0"), "ty": I32}],
            regions=["r0"], rmode=own(), rty=I32)}})

    def test_type7_deref_nonref(self):
        self.expect("TYPE-7", {"structs": {}, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": use(deref(var("x")))}],
            params=[{"name": "x", "mode": own(), "ty": I32}],
            rmode=own(), rty=I32)}})

    def test_type7_deref_reads_referent_ok(self):
        self.ok({"structs": {}, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": use(deref(var("p")))}],
            params=[{"name": "p", "mode": ref("r0"), "ty": I32}],
            regions=["r0"], rmode=own(), rty=I32)}})

    def test_type5_let_mismatch(self):
        self.expect("TYPE-5", {"structs": {}, "enums": {}, "fns": {"f": pfn(
            [{"kind": "let", "name": "a", "mode": own(), "ty": I32, "init": lit(UNIT)},
             {"kind": "return", "expr": lit(UNIT)}])}})

    def test_type5_return_mismatch(self):
        self.expect("TYPE-5", {"structs": {}, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": lit(UNIT)}], rmode=own(), rty=I32)}})

    def test_type5_arg_mismatch(self):
        self.expect("TYPE-5", {"structs": {}, "enums": SIGN,
                    "fns": {"sign_of": SIGN_OF, "g": pfn(
            [{"kind": "return", "expr": ucall("sign_of", ["x"], [lit(UNIT)])}],
            rmode=own(), rty=named("Sign"))}})

    def test_type5_context_free_result_constructor(self):
        flag = {"Flag": [{"variant": "First", "fields": []},
                         {"variant": "Second", "fields": []}]}
        direct = {"kind": "match",
                  "scrut": construct("Err", [("error", construct("First", []))]),
                  "arms": [
                      {"variant": "Ok",
                       "binders": [{"field": "value", "name": "value"}], "body": []},
                      {"variant": "Err",
                       "binders": [{"field": "error", "name": "error"}], "body": []},
                  ]}
        self.expect("TYPE-5", {"structs": {}, "enums": flag,
                    "fns": {"f": pfn([direct, {"kind": "return", "expr": lit(UNIT)}])}})

    def test_type5_context_free_option_constructor(self):
        flag = {"Flag": [{"variant": "First", "fields": []},
                         {"variant": "Second", "fields": []}]}
        direct = {"kind": "match",
                  "scrut": construct("Some", [("value", construct("First", []))]),
                  "arms": [
                      {"variant": "None", "binders": [], "body": []},
                      {"variant": "Some",
                       "binders": [{"field": "value", "name": "value"}], "body": []},
                  ]}
        self.expect("TYPE-5", {"structs": {}, "enums": flag,
                    "fns": {"f": pfn([direct, {"kind": "return", "expr": lit(UNIT)}])}})

    def test_type6_unknown_constructor(self):
        self.expect("TYPE-6", {"structs": {}, "enums": {}, "fns": {"f": pfn(
            [{"kind": "return", "expr": construct("Nope", [])}],
            rmode=own(), rty=named("Q"))}})

    def test_type6_duplicate_variant(self):
        self.expect("TYPE-6", {"structs": {},
                    "enums": {"A": [{"variant": "Dup", "fields": []}],
                              "B": [{"variant": "Dup", "fields": []}]},
                    "fns": {"g": pfn([{"kind": "return", "expr": lit(UNIT)}])}})

    def test_give_type_mismatch(self):
        self.expect("TYPE-5", {"structs": {}, "enums": {}, "fns": {"g": pfn([
            value_match("v", UNIT, [
                {"variant": "Ok", "binders": [{"field": "value", "name": "w"}],
                 "body": [{"kind": "give", "expr": lit(I32)}]},
                {"variant": "Err", "binders": [{"field": "error", "name": "e"}],
                 "body": [{"kind": "return", "expr": lit(UNIT)}]},
            ]),
            {"kind": "return", "expr": lit(UNIT)}])}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
