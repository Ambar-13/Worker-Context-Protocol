"""
Conformance runner: load test bundle, run cases against target, produce report.

v0.955.1 status: all three levels pass against the reference coordinator.
  Level 1 (protocol surface):              7 / 7
  Level 2 (attestation + recheck):        16 / 16
  Level 3 (federation, wire surface):     10 / 10
  Total:                                  33 / 33

The runner supports:
  - `params_template` with `{{key}}` substitution; `{{uuid}}` produces
    a fresh uuid per substitution site
  - `setup_steps`: a list of `{method, params, save_as}` pre-calls
    whose results flow into the case context as `{{step.NAME.key}}`
  - Generator dicts inside params for signed payloads:
      {"_make_acceptance": {"task_id": ..., "worker": "worker"}}
      {"_make_evidence":   {"mode": ..., "kind": ..., "claim_id": ...,
                             "payload": {...}, "worker": "worker"}}
      {"_make_capability": {"worker": "worker", "class": "human"}}
  - Expected validators: `error_code`, `result_keys`, `exact_result`,
    `verifier_decision`, `accepts_post`, `audit_entries_contain`,
    `property_holds`, `task_completed_accounting_ref_matches`,
    `task_voided_attempts_used_matches`,
    `audit_chain_entry_carries_continuation_of`.

The Level 3 cases test federation invariants observable from the
single-coordinator wire surface (federation filter preserved,
constraints.federation honoured as opt-in routing hint, agent_class
informational, local conformance not relaxed for federated tasks).
The full cross-coordinator behaviour is verified by
`wcp_coordinator/tests/test_federation.py` (11 unit tests) and
`examples/federation-demo/demo.py` (in-process two-coordinator demo
that exits 0).
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
        # `{{key}}` substitution plus a small set of generator-dict
        # forms for signed payloads the conformance suite needs:
        #   {"_make_acceptance": {"task_id": "...", "worker": "worker"|"agent"}}
        #     -> a real acceptance_attestation envelope signed by the
        #        named identity.
        #   {"_make_evidence": {"mode": "...", "kind": "...", "claim_id": "...",
        #                       "payload": {...}, "worker": "worker"}}
        #     -> a real signed evidence envelope.
        # `{{uuid}}` is special-cased to a fresh uuid per substitution
        # site so multiple placeholders inside one case do not collide.
        def walk(node: Any) -> Any:
            if isinstance(node, dict):
                # Generator-dict forms.
                if "_make_acceptance" in node:
                    spec = walk(node["_make_acceptance"])
                    return self._make_signed_acceptance(spec, context)
                if "_make_evidence" in node:
                    spec = walk(node["_make_evidence"])
                    return self._make_signed_evidence(spec, context)
                if "_make_capability" in node:
                    spec = walk(node["_make_capability"])
                    return self._make_capability(spec, context)
                return {k: walk(v) for k, v in node.items()}
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

    # --- generator helpers used by `_materialize_params` --------------------

    def _make_signed_acceptance(
        self, spec: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Produce a real acceptance_attestation envelope matching the
        coordinator's claim-validation: signed canonical-JSON over
        (task_id, worker_id, eta, bid, payload_hash, signed_at).

        IMPORTANT: the spec's `eta` MUST equal the eta the outer
        tasks/claim call passes, otherwise the coordinator's
        recomputed canonical bytes will not match the signed bytes
        and verification fails. The test bundle convention is to pass
        the same eta literal in both places, or rely on the default
        (2026-06-01T10:00:00Z) which matches the bundle's claim eta.
        """
        from datetime import datetime, timezone
        identity = self._lookup_identity(spec.get("worker", "worker"), context)
        task_id = spec["task_id"]
        # Default matches the eta used in the bundle's tasks/claim
        # params_template; override via spec.eta when a case uses a
        # different one.
        eta = spec.get("eta", "2026-06-01T10:00:00Z")
        bid = spec.get("bid")
        payload_hash = "0" * 64
        signed_at = spec.get("signed_at") or datetime.now(timezone.utc).isoformat()
        canonical = {
            "task_id": task_id,
            "worker_id": identity.did,
            "eta": eta,
            "bid": bid,
            "payload_hash": payload_hash,
            "signed_at": signed_at,
        }
        sig = identity.sign(canonical)
        return {
            "sig": sig,
            "alg": "Ed25519",
            "payload_hash": payload_hash,
            "signed_at": signed_at,
        }

    def _make_signed_evidence(
        self, spec: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Produce a real signed evidence envelope matching the
        coordinator's attestation validator (mode, kind, payload_hash,
        worker_id, claim_id, collected_at)."""
        from datetime import datetime, timezone
        identity = self._lookup_identity(spec.get("worker", "worker"), context)
        claim_id = spec["claim_id"]
        mode = spec["mode"]
        kind = spec["kind"]
        payload = spec.get("payload", {})
        payload_hash = "0" * 64
        collected_at = spec.get("collected_at") or datetime.now(timezone.utc).isoformat()
        canonical = {
            "mode": mode,
            "kind": kind,
            "payload_hash": payload_hash,
            "worker_id": identity.did,
            "claim_id": claim_id,
            "collected_at": collected_at,
        }
        sig = identity.sign(canonical)
        return {
            "schema_version": "wcp/0.1",
            "mode": mode,
            "kind": kind,
            "payload": payload,
            "payload_hash": payload_hash,
            "sig": sig,
            "worker_id": identity.did,
            "claim_id": claim_id,
            "collected_at": collected_at,
        }

    def _make_capability(
        self, spec: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Produce a capability descriptor for capabilities/upsert with
        sensible defaults that match the conformance fixtures."""
        from datetime import datetime, timezone
        identity = self._lookup_identity(spec.get("worker", "worker"), context)
        principal_did = (
            spec.get("principal_id") or context.get("agent_did") or identity.did
        )
        worker_class = spec.get("class", "human")
        modes = spec.get(
            "attestation_methods_supported",
            ["sensor-witness", "third-party-witness",
             "cryptographic-presence", "owner-sign-off"],
        )
        descriptor_types_supported = spec.get("descriptor_types_supported")
        certifications = spec.get("certifications", [])
        venue_id = spec.get("venue_id", "v1")
        required = {
            "current_location": {"venue_id": venue_id, "map_id": "m1"},
            "available_windows": [
                {"rrule": "FREQ=DAILY;BYHOUR=0-23", "timezone": "UTC"}
            ],
            "attestation_methods_supported": modes,
            "certifications": certifications,
            "policy_windows": [{"type": "geographic", "scope": "global"}],
            "attestation_keys": [
                {"kty": "OKP", "crv": "Ed25519",
                 "x": identity.public_key_b64url}
            ],
            "as_of": datetime.now(timezone.utc).isoformat(),
        }
        if descriptor_types_supported is not None:
            required["descriptor_types_supported"] = descriptor_types_supported
        return {
            "schema_version": "wcp/0.2",
            "worker_id": identity.did,
            "principal_id": principal_did,
            "class": worker_class,
            "required": required,
            "class_extension": spec.get("class_extension", {}),
        }

    def _lookup_identity(self, name: str, context: dict[str, Any]):
        """`name` is "worker", "agent", or "worker.<label>"; the runner
        stashes WorkerIdentity / AgentIdentity instances in context under
        `_identities` so generators can produce signatures."""
        identities = context.get("_identities") or {}
        if name not in identities:
            raise ValueError(
                f"unknown identity {name!r}; available: {sorted(identities)}"
            )
        return identities[name]

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

        # audit_entries_contain: result.event_types is a superset of the
        # listed event types. Designed for cases whose final call is
        # audit/observe (which returns {event_types: [...], ...}).
        if "audit_entries_contain" in expected:
            err = response.get("error")
            if err:
                return False, f"expected audit observe success, got error {err.get('code')}"
            result = response.get("result") or {}
            event_types = set(result.get("event_types") or [])
            missing = [t for t in expected["audit_entries_contain"]
                       if t not in event_types]
            if missing:
                return False, f"audit chain missing event types: {missing}"
            return True, None

        # property_holds: paired with `expected_property` in the params,
        # this evaluates a small fixed set of audit-chain properties
        # over the result of an audit/observe call.
        if "property_holds" in expected:
            err = response.get("error")
            if err:
                return False, f"expected audit observe success, got error {err.get('code')}"
            result = response.get("result") or {}
            return self._check_property_holds(expected, result)

        # task_completed_accounting_ref_matches: the task_completed
        # audit entry's payload.accounting_ref equals the expected value.
        if "task_completed_accounting_ref_matches" in expected:
            result = response.get("result") or {}
            payload = result.get("task_completed_payload") or {}
            want = expected.get("expected_accounting_ref")
            got = payload.get("accounting_ref")
            if want != got:
                return False, f"accounting_ref: want {want!r}, got {got!r}"
            return True, None

        # task_voided_attempts_used_matches: the task_voided audit entry's
        # payload.attempts_used equals the expected integer.
        if "task_voided_attempts_used_matches" in expected:
            result = response.get("result") or {}
            payload = result.get("task_voided_payload") or {}
            want = expected.get("expected_attempts_used")
            got = payload.get("attempts_used")
            if want != got:
                return False, f"attempts_used: want {want!r}, got {got!r}"
            return True, None

        # audit_chain_entry_carries_continuation_of: the task_posted
        # audit entry includes a continuation_of block.
        if "audit_chain_entry_carries_continuation_of" in expected:
            result = response.get("result") or {}
            # observe returned entries: the task_posted one carries
            # continuation_of inside its payload.
            entries = result.get("entries") or []
            for e in entries:
                if e.get("event_type") == "task_posted":
                    if (e.get("payload") or {}).get("continuation_of"):
                        return True, None
            return False, "no task_posted entry carries continuation_of"

        # Validators whose check still requires inspection beyond a
        # single observe call are flagged honestly.
        deferred_validators = {
            "audit_chain_entry_field_preserved",
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

    def _check_property_holds(
        self, expected: dict[str, Any], result: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Evaluate a small fixed set of audit-chain properties."""
        prop = expected.get("expected_property")
        if prop == "verifier_decision_identical_across_attempts":
            decisions = result.get("attempt_verifier_decisions") or []
            if len(decisions) < 2:
                return False, f"need >=2 attempts, saw {len(decisions)}"
            ok = all(d == decisions[0] for d in decisions)
            return (ok, None) if ok else (False, f"decisions varied: {decisions}")
        if prop == "attestation_attempt_entries_match_attempt_count":
            attempt_count = result.get("attestation_attempts")
            event_types = result.get("event_types") or []
            n = sum(1 for t in event_types if t == "attestation_attempt")
            ok = (attempt_count == n) and n > 0
            return (ok, None) if ok else (
                False, f"attempt entries={n}, attestation_attempts={attempt_count}"
            )
        return False, f"unknown property: {prop!r}"


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
        # A second worker identity is used by self-dealing tests where
        # the worker.principal_id must match the agent's DID.
        self_worker_ident = WorkerIdentity.generate()
        context: dict[str, Any] = {
            "worker_did": worker_ident.did,
            "worker_pubkey_b64": worker_ident.public_key_b64url,
            "agent_did": agent_ident.did,
            "self_worker_did": self_worker_ident.did,
            "self_worker_pubkey_b64": self_worker_ident.public_key_b64url,
            "uuid": str(uuid.uuid4()),
            "schema_version": "wcp/0.2",
            "now_iso": datetime.now(timezone.utc).isoformat(),
            "_identities": {
                "worker": worker_ident,
                "agent": agent_ident,
                "self_worker": self_worker_ident,
            },
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
