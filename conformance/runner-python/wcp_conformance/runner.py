"""
Conformance runner: load test bundle, run cases against target, produce report.
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
        params = self._materialize_params(case.params_template, context)
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
                    return context.get(key, node)
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
        if "result_keys" in expected:
            result = response.get("result") or {}
            for k in expected["result_keys"]:
                if k not in result:
                    return False, f"missing result key: {k!r}"
            return True, None
        if "error_code" in expected:
            err = response.get("error") or {}
            if err.get("code") != expected["error_code"]:
                return False, (
                    f"expected error code {expected['error_code']}, got "
                    f"{err.get('code')!r}"
                )
            return True, None
        if "exact_result" in expected:
            if response.get("result") != expected["exact_result"]:
                return False, "result mismatch"
            return True, None
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
