"""Check for duplicate AST nodes after merge."""

from __future__ import annotations

from typing import Final

from mypy.nodes import Decorator, FakeInfo, FuncDef, SymbolNode, Var
from mypy.server.objgraph import get_path, get_reachable_graph

# If True, print more verbose output on failure.
DUMP_MISMATCH_NODES: Final = False


def check_consistency(o: object) -> None:
    """Fail if there are two AST nodes with the same fullname reachable from 'o'.

    Raise AssertionError on failure and print some debugging output.
    """
    seen, parents = get_reachable_graph(o)
    reachable = list(seen.values())
    syms = [x for x in reachable if isinstance(x, SymbolNode)]

    m: dict[str, SymbolNode] = {}
    for sym in syms:
        if isinstance(sym, FakeInfo):
            continue

        fn = sym.fullname
        # ensure there are no None names
        assert fn is not None

        # Skip stuff that should be expected to have duplicate names
        if isinstance(sym, (Var, Decorator)):
            continue
        if isinstance(sym, FuncDef) and sym.is_overload:
            continue

        if fn not in m:
            m[sym.fullname] = sym
            continue

        # We have trouble and need to decide what to do about it.
        sym1, sym2 = sym, m[fn]

        # If the type changed, then it shouldn't have been merged.
        if type(sym1) is not type(sym2):
            continue

        path1 = get_path(sym1, seen, parents)
        path2 = get_path(sym2, seen, parents)

        if fn in m:
            print(f"\nDuplicate {type(sym).__name__!r} nodes with fullname {fn!r} found:")
            print("[1] %d: %s" % (id(sym1), path_to_str(path1)))
            print("[2] %d: %s" % (id(sym2), path_to_str(path2)))

        if DUMP_MISMATCH_NODES and fn in m:
            # Add verbose output with full AST node contents.
            print("---")
            print(id(sym1), sym1)
            print("---")
            print(id(sym2), sym2)

        assert sym.fullname not in m


def path_to_str(path: list[tuple[object, object]]) -> str:
    result = "<root>"
    for attr, obj in path:
        t = type(obj).__name__
        if t in ("dict", "tuple", "SymbolTable", "list"):
            result += f"[{repr(attr)}]"
        else:
            if isinstance(obj, Var):
                result += f".{attr}({t}:{obj.name})"
            elif t in ("BuildManager", "FineGrainedBuildManager"):
                # Omit class name for some classes that aren't part of a class
                # hierarchy since there isn't much ambiguity.
                result += f".{attr}"
            else:
                result += f".{attr}({t})"
    return result
