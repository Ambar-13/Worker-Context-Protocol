"""
v2 Worker class with decorator-style registration.

Wraps v1 `WorkerSession` so v2 callers get a higher-level ergonomic API
without re-implementing the wire protocol.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Optional

from ..canonical import canonical_json_bytes, sha256_hex
from ..identity import WorkerIdentity
from ..rpc_client import RpcClient, WcpRpcError
from ..session import WorkerSession
from ..types import (
    AttestationEvidence,
    AttestationMode,
    CapabilityDescriptor,
    WorkerClass,
)

log = logging.getLogger("wcp_sdk.v2.worker")

HandlerFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]]
AttestFn = Callable[
    [str, dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]
]


@dataclass
class _Capability:
    descriptor_types: tuple[str, ...] = ()
    certifications: tuple[dict[str, Any], ...] = ()
    attestation_methods_supported: tuple[str, ...] = (
        "sensor-witness",
        "third-party-witness",
        "cryptographic-presence",
        "owner-sign-off",
    )
    class_extension: dict[str, Any] = field(default_factory=dict)
    current_location: dict[str, Any] = field(
        default_factory=lambda: {"venue_id": "venue-a", "map_id": "map-a"}
    )
    available_windows: tuple[dict[str, str], ...] = (
        {"rrule": "FREQ=DAILY", "timezone": "UTC"},
    )
    policy_windows: tuple[dict[str, str], ...] = ()


class Worker:
    """Decorator-style WCP worker.

    Construct, decorate handler functions, then call `.run()` to connect.
    """

    def __init__(
        self,
        *,
        name: str,
        worker_class: str | WorkerClass,
        coordinator: str,
        principal_id: str = "did:wcp:example-principal",
        key_path: str | Path | None = None,
    ) -> None:
        self.name = name
        self.worker_class = (
            worker_class if isinstance(worker_class, WorkerClass) else WorkerClass(worker_class)
        )
        self.coordinator = coordinator
        self.principal_id = principal_id

        if key_path is None:
            self.identity = WorkerIdentity.generate()
        else:
            self.identity = WorkerIdentity.load_or_generate(Path(key_path))

        self.did = self.identity.did
        self._capability = _Capability()
        self._handlers: dict[str, HandlerFn] = {}
        self._attesters: dict[AttestationMode, AttestFn] = {}
        self._session: WorkerSession | None = None
        self._loop_task: asyncio.Task[None] | None = None

    # --- decorators ----------------------------------------------------------

    def capability(
        self,
        *,
        descriptor_types: Iterable[str],
        certifications: Iterable[dict[str, Any]] = (),
        attestation_methods_supported: Optional[Iterable[str]] = None,
        class_extension: Optional[dict[str, Any]] = None,
        current_location: Optional[dict[str, Any]] = None,
        available_windows: Optional[Iterable[dict[str, str]]] = None,
        policy_windows: Optional[Iterable[dict[str, str]]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register this worker's capability descriptor."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._capability = _Capability(
                descriptor_types=tuple(descriptor_types),
                certifications=tuple(certifications),
                attestation_methods_supported=tuple(
                    attestation_methods_supported
                    or self._capability.attestation_methods_supported
                ),
                class_extension=dict(class_extension or {}),
                current_location=dict(
                    current_location or self._capability.current_location
                ),
                available_windows=tuple(
                    available_windows or self._capability.available_windows
                ),
                policy_windows=tuple(
                    policy_windows or self._capability.policy_windows
                ),
            )
            return fn

        return decorator

    def handle(self, descriptor_type: str) -> Callable[[HandlerFn], HandlerFn]:
        """Register a handler for a descriptor_type."""

        def decorator(fn: HandlerFn) -> HandlerFn:
            self._handlers[descriptor_type] = fn
            return fn

        return decorator

    def attest(
        self, mode: AttestationMode | str
    ) -> Callable[[AttestFn], AttestFn]:
        """Register an attestation builder for a given mode."""
        if isinstance(mode, str):
            mode = AttestationMode(mode)

        def decorator(fn: AttestFn) -> AttestFn:
            self._attesters[mode] = fn
            return fn

        return decorator

    # --- runtime -------------------------------------------------------------

    def build_descriptor(self) -> CapabilityDescriptor:
        cap = self._capability
        return CapabilityDescriptor(
            worker_id=self.did,
            principal_id=self.principal_id,
            worker_class=self.worker_class,
            current_location=dict(cap.current_location),
            attestation_methods_supported=list(cap.attestation_methods_supported),
            attestation_keys=[
                {"kty": "OKP", "crv": "Ed25519", "x": self.identity.public_key_b64url}
            ],
            available_windows=[dict(w) for w in cap.available_windows],
            certifications=[dict(c) for c in cap.certifications],
            policy_windows=[dict(w) for w in cap.policy_windows],
            class_extension={
                **cap.class_extension,
                "wcp_sdk_v2_descriptor_types": list(cap.descriptor_types),
            },
        )

    def run(self, *, once: bool = False, coordinator: str | None = None) -> None:
        """Synchronous entry point. Connects and serves until interrupted."""
        try:
            asyncio.run(self._run_async(once=once, coordinator=coordinator))
        except KeyboardInterrupt:
            pass

    async def run_async(
        self, *, once: bool = False, coordinator: str | None = None
    ) -> None:
        await self._run_async(once=once, coordinator=coordinator)

    async def _run_async(
        self, *, once: bool, coordinator: str | None
    ) -> None:
        url = coordinator or self.coordinator
        async with WorkerSession(url, self.identity) as session:
            self._session = session
            await session.publish_capabilities(self.build_descriptor())
            log.info("worker %s published capabilities to %s", self.did, url)
            if once:
                return
            # Subscribe to task posts via the RPC client's stream handler.
            stop = asyncio.Event()

            async def stream_handler(event: dict[str, Any]) -> None:
                if event.get("event_type") == "task_posted_for_worker":
                    payload = event.get("payload", {})
                    asyncio.create_task(self._execute_full_lifecycle(payload))

            session.rpc.on_stream_event(stream_handler)

            def _signal_stop(signum: int, frame: Any) -> None:
                stop.set()

            try:
                signal.signal(signal.SIGINT, _signal_stop)
                signal.signal(signal.SIGTERM, _signal_stop)
            except (ValueError, OSError):
                # Not main thread; ignore.
                pass

            await stop.wait()

    async def _execute_full_lifecycle(self, dispatch: dict[str, Any]) -> None:
        """Claim, execute, attest, end-to-end for one dispatched task."""
        task_id = dispatch.get("task_id")
        task = dispatch.get("task") or {}
        descriptor_type = task.get("descriptor_type")
        handler = self._handlers.get(descriptor_type)
        if handler is None:
            log.warning(
                "no handler for descriptor_type=%r; ignoring task_id=%s",
                descriptor_type,
                task_id,
            )
            return
        assert self._session is not None
        eta = datetime.now(timezone.utc).isoformat()
        try:
            claim = await self._session.claim(task_id=task_id, eta=eta)
        except WcpRpcError as exc:
            log.warning("claim failed: %s", exc)
            return
        claim_id = claim["claim_id"]
        await self._session.execute_open(claim_id)
        # Run the handler.
        result = handler(task)
        if inspect.isawaitable(result):
            result = await result

        evidence: list[AttestationEvidence] = []
        for mode, builder in self._attesters.items():
            built = builder(claim_id, task)
            if inspect.isawaitable(built):
                built = await built
            evidence.append(
                self._session.build_evidence(
                    claim_id=claim_id,
                    mode=mode,
                    kind=built["kind"],
                    payload=built["payload"],
                )
            )
        if evidence:
            attest_result = await self._session.attest(claim_id, evidence)
            log.info(
                "attest %s -> verifier_decision=%s",
                claim_id,
                attest_result.get("verifier_decision"),
            )
