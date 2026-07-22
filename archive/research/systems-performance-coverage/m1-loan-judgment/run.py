"""Harness: check every transcribed program, compare to the frozen verdict."""
import sys, ast, os
from checker import check_program
from programs_ast import PROGRAMS


def assert_single_pass():
    """Structural proof of no fixpoint: the checker source contains no `while`
    loop (no iterate-to-convergence), and every AST node is visited at most once
    (enforced at runtime by the `_visited` assertion in Checker.visit)."""
    src = open(os.path.join(os.path.dirname(__file__), 'checker.py')).read()
    tree = ast.parse(src)
    whiles = [n for n in ast.walk(tree) if isinstance(n, ast.While)]
    assert not whiles, f"checker.py has {len(whiles)} while-loop(s): possible fixpoint"
    return "no while-loops; single visit per AST node (runtime-asserted)"


def verdict(prog):
    r = check_program(prog)
    if r == 'ACCEPT':
        return 'ACCEPT', ''
    return 'REJECT', r[1]


def run(only_canonical=False):
    canon, cp, cf = [], 0, 0
    corp_pass, corp_fail, fails = 0, 0, []
    for pid, prog, expected, canonical in PROGRAMS:
        if only_canonical and not canonical:
            continue
        got, reason = verdict(prog)
        ok = (got == expected)
        if canonical:
            canon.append((pid, expected, got, ok, reason))
            cp += ok
            cf += (not ok)
        else:
            corp_pass += ok
            corp_fail += (not ok)
            if not ok:
                fails.append((pid, expected, got, reason))

    print("== Canonical P1-P6 ==")
    print(f"{'id':<6}{'expected':<10}{'got':<10}{'result'}")
    for pid, exp, got, ok, reason in canon:
        print(f"{pid:<6}{exp:<10}{got:<10}{'PASS' if ok else 'FAIL'}"
              + ("" if ok else f"   ({reason})"))
    print(f"canonical: {cp}/{cp+cf} pass")
    if not only_canonical:
        print("\n== Corpus ==")
        print(f"corpus: {corp_pass}/{corp_pass+corp_fail} pass")
        for pid, exp, got, reason in fails:
            print(f"  FAIL {pid}: expected {exp}, got {got}   ({reason})")
    print(f"\nstructural: {assert_single_pass()}")


if __name__ == '__main__':
    run(only_canonical='--canon' in sys.argv)
