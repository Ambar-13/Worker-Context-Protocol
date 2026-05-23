"""
v2 Agent class with simple post / subscribe / task-builder ergonomics.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import AbstractAsyncContextManager
from typing import Any, Awaitable, Callable, Optional

from ..identity import AgentIdentity
from ..session import AgentSession

log = logging.getLogger("wcp_sdk.v2.agent")


class Agent(AbstractAsyncContextManager["Agent"]):
    """Decorator-style WCP agent."""

    def __init__(
        self,
        *,
        name: str,
        coordinator: str,
        identity: Optional[AgentIdentity] = None,
    ) -> None:
        self.name = name
        self.coordinator = coordinator
        self.identity = identity or AgentIdentity.generate()
        self.did = self.identity.did
        self._session: AgentSession | None = None
        self._task_builder: Callable[..., dict[str, Any]] | None = None
        self._capability_handlers: list[
            tuple[dict[str, Any] | None, Callable[[dict[str, Any]], Awaitable[None]]]
        ] = []

    def task_builder(self) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
        """Decorator to register a default task-builder function."""

        def decorator(
            fn: Callable[..., dict[str, Any]],
        ) -> Callable[..., dict[str, Any]]:
            self._task_builder = fn
            return fn

        return decorator

    def on_capability(
        self, *, filter: Optional[dict[str, Any]] = None
    ) -> Callable[
        [Callable[[dict[str, Any]], Awaitable[None]]],
        Callable[[dict[str, Any]], Awaitable[None]],
    ]:
        """Register a handler for capability updates matching `filter`."""

        def decorator(
            fn: Callable[[dict[str, Any]], Awaitable[None]],
        ) -> Callable[[dict[str, Any]], Awaitable[None]]:
            self._capability_handlers.append((filter, fn))
            return fn

        return decorator

    async def __aenter__(self) -> "Agent":
        self._session = await AgentSession.connect(self.coordinator, self.identity)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.__aexit__(exc_type, exc, tb)
            self._session = None

    async def post_task(
        self,
        task: dict[str, Any],
        *,
        bond_ref: str,
        expiry: str,
        supervision: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("Agent.post_task requires async with agent: ...")
        return await self._session.post(
            type("_Td", (), {"to_dict": lambda self: task})(),
            bond_ref=bond_ref,
            expiry=expiry,
            supervision=supervision,
        )

    async def discover_capabilities(
        self, *, filter: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("Agent.discover_capabilities requires async with agent: ...")
        return await self._session.subscribe(filter_dict=filter)

    async def subscribe_attestation(self, *, task_id: str) -> AsyncIterableEvents:
        """Iterate over attestation-related events for a posted task.

        The coordinator emits events on the stream endpoint; this helper
        filters by task_id and yields them.
        """
        if self._session is None:
            raise RuntimeError("Agent.subscribe_attestation requires async with agent: ...")
        return AsyncIterableEvents(self._session, task_id)


class AsyncIterableEvents:
    """Async iterator over stream events filtered by task_id."""

    def __init__(self, session: AgentSession, task_id: str) -> None:
        self._session = session
        self._task_id = task_id
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def handler(event: dict[str, Any]) -> None:
            if (event.get("payload") or {}).get("task_id") == task_id:
                await self._queue.put(event)

        self._session.rpc.on_stream_event(handler)

    def __aiter__(self) -> "AsyncIterableEvents":
        return self

    async def __anext__(self) -> dict[str, Any]:
        return await self._queue.get()
