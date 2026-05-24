"""
Conformance runner: load test bundle, run cases against target, produce report.

v0.955.1 status: Level 1 (7 cases) runs end-to-end against the reference
coordinator with all cases passing. Levels 2 and 3 contain cases whose
fixtures the runner cannot currently mint over the wire (no
`capabilities/upsert` RPC; no built-in two-coordinator fixture for L3).
Those cases are reported as REQUIRES_FIXTURE or fail with -42001
TASK_NOT_FOUND when the fixture would have provided a claim_id. The
underlying invariants are exercised by the unit tests
(`wcp_coordinator/tests/test_lifecycle.py` for L2,
`wcp_coordinator/tests/test_federation.py` and
`examples/federation-demo/demo.py` for L3); the conformance runner is
the wire-level cross-check, and a v0.955.2 deliverable will close the
fixture gap with a dev-only registration RPC.

The runner supports:
  - `params_template` with `{{key}}` substitution and fresh `{{uuid}}`
    per substitution site
  - `setup_steps`: a list of `{method, params, save_as}` pre-calls
    whose results flow into the case context as `{{step.NAME.key}}`
  - Expected validators: `error_code`, `result_keys`, `exact_result`,
    `verifier_decision`, `accepts_post`. Validators that need state
    inspection beyond the current RPC response (audit walk, property
    holds, etc.) are reported as REQUIRES_FIXTURE so the runner
    distinguishes "missing implementation" from "wrong behaviour".
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from wcp_sdk import AgentIdentity, WorkerIdentity
from wcp_sdk.rpc_client import RpcClient, WcpRpcError

log = logging.getLogger("wcp_conformance.runner")


@dataclass
class TestCase:
    id: str
    description: str
    level: int
    method: str
    params_template: dict[str, Any]
    expected: dict[str, Any]
    setup_fixtures: list[str] = field(default_factory=list)
    # Optional multi-step flow: a sequence of `{method, params, save_as}`
    # dicts run before the case's main `method` call. Each step's result
    # is materialized into the context as `step.<save_as>.<key>` for
    # `{{step.NAME.key}}` substitution in later steps and the main call.
    setup_steps: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TestCase":
        return cls(
            id=d["id"],
            description=d.get("description", ""),
            level=int(d["level"]),
            method=d["method"],
            params_template=d.get("params_template", {}),
            expected=d.get("expected", {}),
            setup_fixtures=list(d.get("setup_fixtures", [])),
            setup_steps=list(d.get("setup_steps", [])),
        )


@dataclass
class TestResult:
    id: str
    level: int
    passed: bool
    duration_ms: float
    reason: Optional[str] = None
    response: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None


@dataclass
class ConformanceReport:
    target_url: str
    schema_version: str
    level_requested: int
    level_passed: int
    timestamp: str
    suite_version: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def to_json(self) -> str:
        d = asdict(self)
        d["results"] = [asdict(r) for r in self.results]
        return json.dumps(d, indent=2)


class ConformanceRunner:
    def __init__(self, target_url: str) -> None:
        self.target_url = target_url
        self.rpc = RpcClient(target_url)

    async def connect(self) -> None:
        await self.rpc.connect()

    async def close(self) -> None:
        await self.rpc.close()

    async def run_case(self, case: TestCase, context: dict[str, Any]) -> TestResult:
        start = time.perf_counter()
        # Build a per-case context fork so setup_steps don't leak across
        # cases sharing the same runner.
        case_ctx = dict(context)

        # Execute setup_steps. Each step's result is stored under
        # `step.<save_as>.<key>` so later steps and the main call can
        # substitute via `{{step.NAME.key}}`.
        for idx, step in enumerate(case.setup_steps):
            step_method = step.get("method")
            step_params = self._materialize_params(
                step.get("params", {}), case_ctx
            )
            save_as = step.get("save_as", f"step{idx}")
            try:
                step_result = await self.rpc.call(step_method, step_params)
            except WcpRpcError as exc:
                if step.get("ignore_error"):
                    continue
                duration = (time.perf_counter() - start) * 1000.0
                return TestResult(
                    id=case.id, level=case.level, passed=False,
                    duration_ms=duration,
                    reason=f"setup step {save_as!r} failed: {exc.code} {exc.message}",
                    error={"code": exc.code, "message": exc.message},
                )
            # Flatten step result under step.<save_as>.<key> for substitution.
            for k, v in (step_result or {}).items():
                case_ctx[f"step.{save_as}.{k}"] = v

        params = self._materialize_params(case.params_template, case_ctx)
        try:
            result = await self.rpc.call(case.method, params)
            response = {"result": result, "error": None}
            outcome_ok, reason = self._check_expected(case.expected, response)
        except WcpRpcError as exc:
            response = {
                "result": None,
                "error": {"code": exc.code, "message": exc.message, "data": exc.data},
            }
            outcome_ok, reason = self._check_expected(case.expected, response)
        duration = (time.perf_counter() - start) * 1000.0
        return TestResult(
            id=case.id,
            level=case.level,
            passed=outcome_ok,
            duration_ms=duration,
            reason=None if outcome_ok else reason,
            response=response.get("result"),
            error=response.get("error"),
        )

    def _materialize_params(
        self, template: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        # Simple {{key}} substitution; recursively walks template.
        # `{{uuid}}` is special-cased to produce a fresh uuid per
        # substitution site (not per run), so a single test case can
        # safely use multiple {{uuid}} placeholders for distinct ids.
        def walk(node: Any) -> Any:
            if isinstance(node, str):
                if node.startswith("{{") and node.endswith("}}"):
                    key = node[2:-2].strip()
                    if key == "uuid":
                        return str(uuid.uuid4())
                    # Direct hit (includes dotted "step.NAME.key" entries).
                    if key in context:
                        return context[key]
                    # Tolerant dotted access: walk nested dicts under the
                    # first segment when no direct entry exists.
                    if "." in key:
                        parts = key.split(".")
                        cur: Any = context.get(parts[0])
                        for p in parts[1:]:
                            if isinstance(cur, dict) and p in cur:
                                cur = cur[p]
                            else:
                                cur = None
                                break
                        if cur is not None:
                            return cur
                    return node
                # Inline {{uuid}} inside a longer string (e.g.
                # "test-bond-{{uuid}}") is also expanded.
                if "{{uuid}}" in node:
                    parts: list[str] = []
                    i = 0
                    while i < len(node):
                        j = node.find("{{uuid}}", i)
                        if j == -1:
                            parts.append(node[i:])
                            break
                        parts.append(node[i:j])
                        parts.append(str(uuid.uuid4()))
                        i = j + len("{{uuid}}")
                    return "".join(parts)
                return node
            if isinstance(node, dict):
                return {k: walk(v) for k, v in node.items()}
            if isinstance(node, list):
                return [walk(x) for x in node]
            return node
        return walk(template)

    def _check_expected(
        self, expected: dict[str, Any], response: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        # error_code: response is an error with this specific code.
        if "error_code" in expected:
            err = response.get("error") or {}
            if err.get("code") != expected["error_code"]:
                return False, (
                    f"expected error code {expected['error_code']}, got "
                    f"{err.get('code')!r}"
                )
            return True, None

        # result_keys: response is a success with all listed keys present.
        if "result_keys" in expected:
            err = response.get("error")
            if err:
                return False, (
                    f"expected success with keys, got error code "
                    f"{err.get('code')}: {err.get('message')}"
                )
            result = response.get("result") or {}
            for k in expected["result_keys"]:
                if k not in result:
                    return False, f"missing result key: {k!r}"
            return True, None

        # exact_result: byte-equal result match.
        if "exact_result" in expected:
            if response.get("result") != expected["exact_result"]:
                return False, "result mismatch"
            return True, None

        # verifier_decision: succeeds when result.verifier_decision matches.
        if "verifier_decision" in expected:
            result = response.get("result") or {}
            actual = result.get("verifier_decision")
            if actual != expected["verifier_decision"]:
                return False, (
                    f"expected verifier_decision={expected['verifier_decision']!r}, "
                    f"got {actual!r}"
                )
            return True, None

        # accepts_post: succeeds when result has a task_id (alias for the
        # common pattern of "tasks/post should not error").
        if "accepts_post" in expected:
            err = response.get("error")
            if expected["accepts_post"] and err:
                return False, f"expected accept, got error {err.get('code')}"
            if not expected["accepts_post"] and not err:
                return False, "expected refusal, got accept"
            return True, None

        # Validators whose check requires inspecting state outside the
        # current JSON-RPC response (audit chain walk, federation state,
        # multi-step property checks) are flagged honestly. Future runner
        # extensions can implement these once a side-channel for state
        # inspection lands. Until then we mark these "REQUIRES_FIXTURE"
        # rather than failing them as misconfigured.
        deferred_validators = {
            "property_holds",
            "audit_entries_contain",
            "audit_chain_entry_field_preserved",
            "audit_chain_entry_carries_continuation_of",
            "task_completed_accounting_ref_matches",
            "task_voided_attempts_used_matches",
            "matching_invariant",
            "resolves_prior_claim_id",
            "both_chains_carry_continuation_of",
            "federation_uses_only_existing_rpcs",
            "agent_class_preserved_on_both_chains",
            "no_matching_branch_on_agent_class",
        }
        deferred_hits = set(expected) & deferred_validators
        if deferred_hits:
            return False, (
                "REQUIRES_FIXTURE: runner does not yet evaluate "
                + ", ".join(sorted(deferred_hits))
            )

        return False, "no expected criterion defined"


async def run_level(
    target_url: str,
    level: int,
    bundle_path: Path,
) -> ConformanceReport:
    bundle = json.loads(bundle_path.read_text())
    cases = [TestCase.from_dict(c) for c in bundle.get("cases", [])]
    runner = ConformanceRunner(target_url)
    await runner.connect()
    try:
        # Build a per-run context with fresh DIDs for fixtures referenced by tests.
        worker_ident = WorkerIdentity.generate()
        agent_ident = AgentIdentity.generate()
        context: dict[str, Any] = {
            "worker_did": worker_ident.did,
            "worker_pubkey_b64": worker_ident.public_key_b64url,
            "agent_did": agent_ident.did,
            "uuid": str(uuid.uuid4()),
            "schema_version": "wcp/0.2",
            "now_iso": datetime.now(timezone.utc).isoformat(),
        }
        report = ConformanceReport(
            target_url=target_url,
            schema_version="wcp/0.2",
            level_requested=level,
            level_passed=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            suite_version="1.0.0rc1",
        )
        for case in cases:
            if case.level > level:
                continue
            result = await runner.run_case(case, context)
            report.results.append(result)
        report.level_passed = level if report.passed_count == report.total else 0
        return report
    finally:
        await runner.close()
