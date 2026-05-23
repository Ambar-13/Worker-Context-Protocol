"""
RFC 0033 preview: Attestation Key Trust Classes.

Provides:
- TrustClass enum with the six initial registered classes
- declare_trust_class(key, class_) capability descriptor builder helper
- verify_minimum_trust_class(task_descriptor, worker_capability) -> bool
- TaskBuilder.with_minimum_trust_class for the agent side

Trust class is an optional declaration on each attestation_keys[] entry in
a CapabilityDescriptor. Tasks may require a minimum trust class via
attestation_requirement.minimum_trust_class.

This preview implements the partial ordering documented in RFC 0033:
    software-keypair < {hardware-attested-*} < delegated

with `delegated` placed above only when delegation terminates at a
hardware-attested root.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from . import emit_preview_warning


class TrustClass(str, Enum):
    """Registered trust classes per RFC 0033."""

    SOFTWARE_KEYPAIR = "software-keypair"
    HARDWARE_ATTESTED_TPM2 = "hardware-attested-tpm2"
    HARDWARE_ATTESTED_WEBAUTHN = "hardware-attested-webauthn"
    HARDWARE_ATTESTED_SECURE_ENCLAVE = "hardware-attested-secure-enclave"
    HARDWARE_ATTESTED_TEE = "hardware-attested-tee"
    DELEGATED = "delegated"


_HARDWARE_ATTESTED = {
    TrustClass.HARDWARE_ATTESTED_TPM2,
    TrustClass.HARDWARE_ATTESTED_WEBAUTHN,
    TrustClass.HARDWARE_ATTESTED_SECURE_ENCLAVE,
    TrustClass.HARDWARE_ATTESTED_TEE,
}


def is_hardware_attested(tc: TrustClass) -> bool:
    """True if the trust class is in the hardware-attested family."""
    return tc in _HARDWARE_ATTESTED


def is_at_least(
    declared: TrustClass, minimum: TrustClass, *, strict: bool = False
) -> bool:
    """True if `declared` satisfies the `minimum` requirement.

    Ordering per RFC 0033:
        software-keypair < {hardware-attested-*} < delegated
        (delegated is above only when its terminator is hardware-attested;
        strict=True excludes delegated from satisfying hardware-attested-*)

    Strict mode (strict=True):
        - declared MUST be exactly equal to a hardware-attested-* class
          when minimum is hardware-attested-*
        - delegated is excluded from satisfying hardware-attested-*
        - software-keypair satisfies only software-keypair

    Non-strict (default):
        - any hardware-attested-* satisfies any hardware-attested-* minimum
        - delegated satisfies any minimum (assumes delegation terminates
          at an appropriate root)
        - software-keypair satisfies only software-keypair
    """
    emit_preview_warning(33, "trust_classes")
    if declared == minimum:
        return True
    if minimum == TrustClass.SOFTWARE_KEYPAIR:
        return True  # anything satisfies the floor
    if is_hardware_attested(minimum):
        if strict:
            # Strict mode: declared MUST equal minimum exactly (already
            # checked above). Cross-hardware acceptance and delegated to
            # hardware acceptance are both forbidden in strict mode.
            return False
        if is_hardware_attested(declared):
            return True  # any HW satisfies any HW minimum (non-strict)
        if declared == TrustClass.DELEGATED:
            return True
        return False
    if minimum == TrustClass.DELEGATED:
        # Requesting delegated specifically; only delegated qualifies
        return declared == TrustClass.DELEGATED
    return False


@dataclass
class AttestationKeyEntry:
    """One entry in CapabilityDescriptor.attestation_keys[]."""

    key_id: str
    did: str
    public_key_multibase: str
    algorithm: str = "Ed25519"
    trust_class: TrustClass = TrustClass.SOFTWARE_KEYPAIR

    def to_dict(self) -> dict[str, Any]:
        emit_preview_warning(33, "trust_classes")
        return {
            "key_id": self.key_id,
            "did": self.did,
            "public_key_multibase": self.public_key_multibase,
            "algorithm": self.algorithm,
            "trust_class": self.trust_class.value,
        }


def declare_trust_class(
    key_entry: dict[str, Any], trust_class: TrustClass
) -> dict[str, Any]:
    """Add or update the trust_class field on an attestation_keys entry.

    Mutates and returns the entry dict.
    """
    emit_preview_warning(33, "trust_classes")
    key_entry["trust_class"] = trust_class.value
    return key_entry


def verify_minimum_trust_class(
    task_descriptor: dict[str, Any],
    worker_capability: dict[str, Any],
    *,
    key_id: Optional[str] = None,
) -> bool:
    """Verify that the worker's attestation key meets the task's minimum trust class.

    If task_descriptor.attestation_requirement.minimum_trust_class is absent,
    accepts any worker key (defaults to software-keypair acceptance).

    If `key_id` is provided, checks only that specific key; otherwise checks
    that ANY key on the worker satisfies the minimum.

    Returns True if accepted, False if rejected.
    """
    emit_preview_warning(33, "trust_classes")
    req = task_descriptor.get("attestation_requirement", {})
    minimum_str = req.get("minimum_trust_class")
    if not minimum_str:
        return True  # no requirement; accept

    try:
        minimum = TrustClass(minimum_str)
    except ValueError:
        # Unknown trust class string in the requirement; reject conservatively
        return False

    strict = bool(req.get("minimum_trust_class_strict", False))

    keys = worker_capability.get("attestation_keys", []) or worker_capability.get(
        "required", {}
    ).get("attestation_keys", [])
    if not keys:
        return False

    for k in keys:
        if key_id is not None and k.get("key_id") != key_id:
            continue
        declared_str = k.get("trust_class", TrustClass.SOFTWARE_KEYPAIR.value)
        try:
            declared = TrustClass(declared_str)
        except ValueError:
            continue
        if is_at_least(declared, minimum, strict=strict):
            return True
    return False


@dataclass
class TaskBuilder:
    """Lightweight builder for tasks with attestation requirements.

    Used to attach minimum_trust_class to a task descriptor under construction.
    Does not replace the canonical v1.0-rc1 TaskDescriptor schema; this is a
    preview helper for the v1.1 candidate field.
    """

    task: dict[str, Any]

    def with_minimum_trust_class(
        self, trust_class: TrustClass, *, strict: bool = False
    ) -> "TaskBuilder":
        """Add minimum_trust_class (and optional strict flag) to the task."""
        emit_preview_warning(33, "trust_classes")
        req = self.task.setdefault("attestation_requirement", {})
        req["minimum_trust_class"] = trust_class.value
        if strict:
            req["minimum_trust_class_strict"] = True
        return self

    def build(self) -> dict[str, Any]:
        return self.task
