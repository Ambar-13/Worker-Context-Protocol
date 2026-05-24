//! Identity and signing tests for the Rust SDK.

use serde_json::json;
use wcp_sdk::identity::{AgentIdentity, WorkerIdentity};

#[test]
fn worker_did_has_wcp_prefix_and_decodable_pubkey() {
    let w = WorkerIdentity::generate();
    assert!(w.did.starts_with("did:wcp:"));
    // The b64url public key is 32 raw bytes -> 43 chars without padding.
    assert_eq!(w.public_key_b64url.len(), 43);
}

#[test]
fn agent_did_has_wcp_prefix() {
    let a = AgentIdentity::generate();
    assert!(a.did.starts_with("did:wcp:"));
}

#[test]
fn two_generated_identities_differ() {
    let w1 = WorkerIdentity::generate();
    let w2 = WorkerIdentity::generate();
    assert_ne!(w1.did, w2.did);
}

#[test]
fn signature_is_ed25519_prefixed_urlsafe_base64() {
    let w = WorkerIdentity::generate();
    let sig = w.sign(&json!({"a": 1}));
    assert!(sig.starts_with("ed25519:"));
    // 64-byte signature -> 86 chars unpadded urlsafe base64.
    let body = sig.strip_prefix("ed25519:").unwrap();
    assert_eq!(body.len(), 86);
}

#[test]
fn signature_is_deterministic_for_identical_canonical_form() {
    // Ed25519 signatures are deterministic per RFC 8032; canonical JSON
    // ensures the byte input is identical regardless of input field order.
    let w = WorkerIdentity::generate();
    let s1 = w.sign(&json!({"b": 2, "a": 1}));
    let s2 = w.sign(&json!({"a": 1, "b": 2}));
    assert_eq!(s1, s2);
}

#[test]
fn signature_depends_on_payload() {
    let w = WorkerIdentity::generate();
    let s1 = w.sign(&json!({"a": 1}));
    let s2 = w.sign(&json!({"a": 2}));
    assert_ne!(s1, s2);
}

#[test]
fn agent_and_worker_signatures_are_distinct_keys() {
    let w = WorkerIdentity::generate();
    let a = AgentIdentity::generate();
    let payload = json!({"task_id": "t1"});
    assert_ne!(w.sign(&payload), a.sign(&payload));
}
