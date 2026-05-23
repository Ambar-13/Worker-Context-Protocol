"""Tests for wcp_sdk.preview.trust_classes (RFC 0033 preview)."""
from __future__ import annotations

from wcp_sdk.preview.trust_classes import (
    AttestationKeyEntry,
    TaskBuilder,
    TrustClass,
    declare_trust_class,
    is_at_least,
    is_hardware_attested,
    verify_minimum_trust_class,
)


def test_software_keypair_satisfies_software_keypair():
    assert is_at_least(TrustClass.SOFTWARE_KEYPAIR, TrustClass.SOFTWARE_KEYPAIR)


def test_software_keypair_does_not_satisfy_hardware():
    assert not is_at_least(
        TrustClass.SOFTWARE_KEYPAIR, TrustClass.HARDWARE_ATTESTED_TPM2
    )


def test_hardware_tpm2_satisfies_hardware_tpm2():
    assert is_at_least(
        TrustClass.HARDWARE_ATTESTED_TPM2, TrustClass.HARDWARE_ATTESTED_TPM2
    )


def test_hardware_webauthn_satisfies_hardware_tpm2_non_strict():
    # Any hardware-attested-* satisfies any hardware-attested-* (non-strict)
    assert is_at_least(
        TrustClass.HARDWARE_ATTESTED_WEBAUTHN, TrustClass.HARDWARE_ATTESTED_TPM2
    )


def test_hardware_webauthn_does_not_satisfy_hardware_tpm2_strict():
    assert not is_at_least(
        TrustClass.HARDWARE_ATTESTED_WEBAUTHN,
        TrustClass.HARDWARE_ATTESTED_TPM2,
        strict=True,
    )


def test_delegated_satisfies_hardware_non_strict():
    assert is_at_least(
        TrustClass.DELEGATED, TrustClass.HARDWARE_ATTESTED_TPM2, strict=False
    )


def test_delegated_does_not_satisfy_hardware_strict():
    assert not is_at_least(
        TrustClass.DELEGATED, TrustClass.HARDWARE_ATTESTED_TPM2, strict=True
    )


def test_any_satisfies_software_keypair_floor():
    for declared in TrustClass:
        assert is_at_least(declared, TrustClass.SOFTWARE_KEYPAIR)


def test_only_delegated_satisfies_delegated_minimum():
    assert is_at_least(TrustClass.DELEGATED, TrustClass.DELEGATED)
    assert not is_at_least(
        TrustClass.HARDWARE_ATTESTED_TPM2, TrustClass.DELEGATED
    )
    assert not is_at_least(TrustClass.SOFTWARE_KEYPAIR, TrustClass.DELEGATED)


def test_is_hardware_attested_helper():
    assert is_hardware_attested(TrustClass.HARDWARE_ATTESTED_TPM2)
    assert is_hardware_attested(TrustClass.HARDWARE_ATTESTED_WEBAUTHN)
    assert is_hardware_attested(TrustClass.HARDWARE_ATTESTED_SECURE_ENCLAVE)
    assert is_hardware_attested(TrustClass.HARDWARE_ATTESTED_TEE)
    assert not is_hardware_attested(TrustClass.SOFTWARE_KEYPAIR)
    assert not is_hardware_attested(TrustClass.DELEGATED)


def test_attestation_key_entry_to_dict():
    entry = AttestationKeyEntry(
        key_id="primary",
        did="did:wcp:zABC123",
        public_key_multibase="zABC123",
        trust_class=TrustClass.HARDWARE_ATTESTED_TPM2,
    )
    out = entry.to_dict()
    assert out["trust_class"] == "hardware-attested-tpm2"
    assert out["algorithm"] == "Ed25519"


def test_declare_trust_class_mutates_dict():
    key_entry = {
        "key_id": "primary",
        "did": "did:wcp:zABC",
        "public_key_multibase": "zABC",
    }
    declare_trust_class(key_entry, TrustClass.HARDWARE_ATTESTED_WEBAUTHN)
    assert key_entry["trust_class"] == "hardware-attested-webauthn"


def test_verify_minimum_trust_class_no_requirement_accepts():
    task = {"attestation_requirement": {}}
    cap = {
        "attestation_keys": [
            {"key_id": "k1", "trust_class": "software-keypair"}
        ]
    }
    assert verify_minimum_trust_class(task, cap) is True


def test_verify_minimum_trust_class_software_meets_software():
    task = {"attestation_requirement": {"minimum_trust_class": "software-keypair"}}
    cap = {"attestation_keys": [{"key_id": "k1", "trust_class": "software-keypair"}]}
    assert verify_minimum_trust_class(task, cap) is True


def test_verify_minimum_trust_class_software_rejected_for_hardware():
    task = {
        "attestation_requirement": {"minimum_trust_class": "hardware-attested-tpm2"}
    }
    cap = {"attestation_keys": [{"key_id": "k1", "trust_class": "software-keypair"}]}
    assert verify_minimum_trust_class(task, cap) is False


def test_verify_minimum_trust_class_hardware_meets_hardware():
    task = {
        "attestation_requirement": {"minimum_trust_class": "hardware-attested-tpm2"}
    }
    cap = {
        "attestation_keys": [
            {"key_id": "k1", "trust_class": "hardware-attested-webauthn"}
        ]
    }
    assert verify_minimum_trust_class(task, cap) is True  # non-strict


def test_verify_minimum_trust_class_strict_rejects_cross_hardware():
    task = {
        "attestation_requirement": {
            "minimum_trust_class": "hardware-attested-tpm2",
            "minimum_trust_class_strict": True,
        }
    }
    cap = {
        "attestation_keys": [
            {"key_id": "k1", "trust_class": "hardware-attested-webauthn"}
        ]
    }
    assert verify_minimum_trust_class(task, cap) is False


def test_verify_minimum_trust_class_default_is_software_keypair():
    # Capability with NO trust_class declared defaults to software-keypair
    task = {
        "attestation_requirement": {"minimum_trust_class": "hardware-attested-tpm2"}
    }
    cap = {"attestation_keys": [{"key_id": "k1"}]}
    assert verify_minimum_trust_class(task, cap) is False


def test_verify_minimum_trust_class_no_keys_rejects():
    task = {
        "attestation_requirement": {"minimum_trust_class": "hardware-attested-tpm2"}
    }
    cap = {"attestation_keys": []}
    assert verify_minimum_trust_class(task, cap) is False


def test_verify_minimum_trust_class_key_id_filter():
    task = {
        "attestation_requirement": {"minimum_trust_class": "hardware-attested-tpm2"}
    }
    cap = {
        "attestation_keys": [
            {"key_id": "soft", "trust_class": "software-keypair"},
            {"key_id": "hard", "trust_class": "hardware-attested-tpm2"},
        ]
    }
    # Asking for 'hard' specifically: passes
    assert verify_minimum_trust_class(task, cap, key_id="hard") is True
    # Asking for 'soft' specifically: fails
    assert verify_minimum_trust_class(task, cap, key_id="soft") is False
    # No filter: passes because at least one key qualifies
    assert verify_minimum_trust_class(task, cap) is True


def test_task_builder_with_minimum_trust_class():
    task: dict = {}
    builder = TaskBuilder(task)
    built = (
        builder.with_minimum_trust_class(TrustClass.HARDWARE_ATTESTED_TPM2).build()
    )
    assert built["attestation_requirement"]["minimum_trust_class"] == (
        "hardware-attested-tpm2"
    )
    assert "minimum_trust_class_strict" not in built["attestation_requirement"]


def test_task_builder_strict_flag():
    task: dict = {"attestation_requirement": {"existing": "preserved"}}
    builder = TaskBuilder(task)
    built = builder.with_minimum_trust_class(
        TrustClass.HARDWARE_ATTESTED_TPM2, strict=True
    ).build()
    assert built["attestation_requirement"]["minimum_trust_class_strict"] is True
    assert built["attestation_requirement"]["existing"] == "preserved"


def test_verify_minimum_trust_class_unknown_requirement_rejects():
    task = {"attestation_requirement": {"minimum_trust_class": "made-up-class"}}
    cap = {"attestation_keys": [{"key_id": "k1", "trust_class": "software-keypair"}]}
    assert verify_minimum_trust_class(task, cap) is False
