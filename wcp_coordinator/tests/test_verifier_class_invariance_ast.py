"""Static AST check: the attestation_verifier package MUST NOT branch on
worker class.

The verifier's load-bearing invariant (paper Section 3, the D4 forcing
function) is that it discriminates by (mode, kind) alone — never by
the worker's class. The class-invariance property test
(`test_verifier_class_invariance.py`) tests this dynamically over
generated (mode, kind, payload) triples, but a property test can only
catch a regression on branches its generator actually exercises. A
future contributor adding a branch behind a rarely-hit predicate could
slip past it.

This AST check is the static counterpart: walk every .py file under
`wcp_coordinator/attestation_verifier/`, parse to AST, find every
`Compare` and `Match` node, and fail if any of them references an
identifier or string literal that names a worker class.

If you find yourself wanting to disable this test to land a per-class
branch, stop. The branch belongs in the application-layer descriptor
(`class_extension`), not in the verifier.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


VERIFIER_PKG = Path(__file__).resolve().parent.parent / "attestation_verifier"

# Identifier names that, if compared against in the verifier, would
# represent a class branch. `worker_class` is the descriptor field name;
# `class_` is the SQLAlchemy column attribute (Worker.class_ aliased
# from the reserved "class" Python keyword) — both are equivalent
# branch surfaces.
FORBIDDEN_IDENTIFIERS = frozenset({"worker_class", "class_"})

# String literals that, if compared against, would mean someone is
# branching on the WorkerClass enum's wire form even without naming
# the field directly. Sourced from wcp_coordinator.models.WorkerClass.
FORBIDDEN_LITERALS = frozenset({
    "human",
    "autonomous_robot",
    "teleoperated_robot",
    "semi_autonomous",
    "hybrid",
})


def _file_pairs() -> list[tuple[Path, ast.AST]]:
    pairs: list[tuple[Path, ast.AST]] = []
    for path in sorted(VERIFIER_PKG.glob("*.py")):
        if path.name == "__pycache__":
            continue
        src = path.read_text(encoding="utf-8")
        pairs.append((path, ast.parse(src, filename=str(path))))
    return pairs


def _node_names(node: ast.AST) -> set[str]:
    """Collect every identifier name referenced inside `node`."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _node_attr_tails(node: ast.AST) -> set[str]:
    """Collect every attribute-access tail (`.x` in `a.b.x`) inside `node`.
    This catches `task.worker_class`, `worker.class_`, etc."""
    return {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


def _node_string_literals(node: ast.AST) -> set[str]:
    """Collect every string literal inside `node`."""
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)
    return out


def _branch_nodes(tree: ast.AST):
    """Yield every Compare and Match node anywhere in the tree."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.Compare, ast.Match)):
            yield n


def test_verifier_has_no_worker_class_branch_in_compare_or_match():
    violations: list[str] = []
    for path, tree in _file_pairs():
        for branch in _branch_nodes(tree):
            names = _node_names(branch)
            attrs = _node_attr_tails(branch)
            literals = _node_string_literals(branch)

            bad_idents = (names | attrs) & FORBIDDEN_IDENTIFIERS
            bad_literals = literals & FORBIDDEN_LITERALS

            if bad_idents or bad_literals:
                node_kind = type(branch).__name__
                line = getattr(branch, "lineno", "?")
                detail = []
                if bad_idents:
                    detail.append(f"identifiers={sorted(bad_idents)}")
                if bad_literals:
                    detail.append(f"literals={sorted(bad_literals)}")
                violations.append(
                    f"{path.relative_to(VERIFIER_PKG.parent)}:{line} "
                    f"{node_kind} -> {' '.join(detail)}"
                )

    if violations:
        msg = (
            "the attestation_verifier package contains a class-branching "
            "Compare or Match node. The verifier MUST NOT branch on worker "
            "class; class-specific behaviour belongs in the application-"
            "layer descriptor (class_extension). Violations:\n  "
            + "\n  ".join(violations)
        )
        pytest.fail(msg)


def test_verifier_pkg_has_at_least_one_module():
    """Sanity: the AST walk above is meaningless if the glob returns nothing."""
    pairs = _file_pairs()
    assert len(pairs) >= 5, (
        f"expected the verifier package to ship at least 5 modules; "
        f"found {[p.name for p, _ in pairs]}"
    )
