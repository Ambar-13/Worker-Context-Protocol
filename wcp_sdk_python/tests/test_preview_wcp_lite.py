"""Tests for wcp_sdk.preview.wcp_lite (RFC 0029 preview)."""
from __future__ import annotations

import asyncio

import pytest

from wcp_sdk.preview import wcp_lite as lite
from wcp_sdk.preview.wcp_lite import (
    BufferedAuditChain,
    BufferOverflowError,
    build_intermittent_capability_extension,
    build_task_constraint_for_intermittent_executor,
)


def make_entry(chain: BufferedAuditChain, n: int) -> None:
    chain.append(
        entry_id=f"e{n:04d}",
        task_id="task-1",
        claim_id="claim-1",
        signer_did=chain.worker_did,
        payload={"event": f"step_{n}"},
        signature=f"ed25519:stub-sig-{n}",
    )


def test_append_links_hashes_correctly():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorkerX")
    make_entry(chain, 1)
    make_entry(chain, 2)
    make_entry(chain, 3)
    entries = list(chain.entries_for_replay())
    assert entries[0].previous_entry_hash is None
    assert entries[1].previous_entry_hash == entries[0].entry_hash
    assert entries[2].previous_entry_hash == entries[1].entry_hash


def test_verify_chain_integrity_intact():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorkerY")
    for n in range(5):
        make_entry(chain, n)
    assert chain.verify_chain_integrity() is True


def test_verify_chain_integrity_detects_tamper():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorkerZ")
    for n in range(3):
        make_entry(chain, n)
    entries = list(chain.entries_for_replay())
    # Mutate an entry's payload after the fact (simulating tamper); entry_hash
    # no longer matches its body.
    entries[1].payload = {"event": "tampered"}
    assert chain.verify_chain_integrity() is False


def test_buffer_overflow_raises():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorkerSmall", capacity=3)
    for n in range(3):
        make_entry(chain, n)
    with pytest.raises(BufferOverflowError) as exc_info:
        make_entry(chain, 3)
    assert exc_info.value.capacity == 3
    assert exc_info.value.attempted_count == 4


def test_is_full_threshold():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorker", capacity=2)
    assert not chain.is_full
    make_entry(chain, 0)
    assert not chain.is_full
    make_entry(chain, 1)
    assert chain.is_full


@pytest.mark.asyncio
async def test_replay_on_reconnect_success():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorker")
    for n in range(3):
        make_entry(chain, n)
    submitted = []

    async def submit(batch):
        submitted.extend(batch)
        return True

    accepted = await chain.replay_on_reconnect(submit)
    assert accepted is True
    assert len(submitted) == 3
    assert len(chain) == 0  # cleared after success


@pytest.mark.asyncio
async def test_replay_on_reconnect_keeps_buffer_on_rejection():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorker")
    for n in range(2):
        make_entry(chain, n)

    async def submit(batch):
        return False

    accepted = await chain.replay_on_reconnect(submit)
    assert accepted is False
    assert len(chain) == 2  # buffer NOT cleared on rejection


@pytest.mark.asyncio
async def test_replay_empty_buffer_is_noop():
    chain = BufferedAuditChain(worker_did="did:wcp:zWorker")
    called = False

    async def submit(batch):
        nonlocal called
        called = True
        return True

    accepted = await chain.replay_on_reconnect(submit)
    assert accepted is True
    assert called is False  # no batch, no submit call


def test_build_intermittent_capability_extension():
    ext = build_intermittent_capability_extension(
        max_offline_duration_seconds=3600,
        expected_disconnect_pattern="predictable",
        buffer_capacity_audit_entries=5000,
    )
    assert ext["connectivity_profile"] == lite.CONNECTIVITY_INTERMITTENT
    assert ext["max_offline_duration_seconds"] == 3600
    assert ext["expected_disconnect_pattern"] == "predictable"
    assert ext["buffer_capacity_audit_entries"] == 5000


def test_build_intermittent_capability_extension_rejects_bad_pattern():
    with pytest.raises(ValueError, match="predictable"):
        build_intermittent_capability_extension(
            max_offline_duration_seconds=600,
            expected_disconnect_pattern="invalid_pattern",
        )


def test_build_intermittent_capability_extension_rejects_nonpositive_duration():
    with pytest.raises(ValueError, match="positive"):
        build_intermittent_capability_extension(max_offline_duration_seconds=0)


def test_build_task_constraint_for_intermittent_executor():
    c = build_task_constraint_for_intermittent_executor(
        accepts_intermittent_executor=True,
        max_acceptable_offline_seconds=1800,
    )
    assert c["accepts_intermittent_executor"] is True
    assert c["max_acceptable_offline_seconds"] == 1800


def test_build_task_constraint_omits_optional():
    c = build_task_constraint_for_intermittent_executor(
        accepts_intermittent_executor=False,
    )
    assert c == {"accepts_intermittent_executor": False}
