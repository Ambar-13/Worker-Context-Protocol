//! Cross-language canonical JSON regression coverage.
//!
//! These vectors are byte-identical to the Python and TypeScript SDKs'
//! canonical encoders. The whole point of canonical JSON is that all
//! three implementations sign the same bytes for the same logical
//! payload.

use serde_json::json;
use wcp_sdk::canonical::{canonical_json, sha256_hex};

#[test]
fn primitives_match_python() {
    assert_eq!(canonical_json(&json!(null)), "null");
    assert_eq!(canonical_json(&json!(true)), "true");
    assert_eq!(canonical_json(&json!(false)), "false");
    assert_eq!(canonical_json(&json!(0)), "0");
    assert_eq!(canonical_json(&json!(-42)), "-42");
    assert_eq!(canonical_json(&json!("hello")), r#""hello""#);
}

#[test]
fn empty_containers() {
    assert_eq!(canonical_json(&json!({})), "{}");
    assert_eq!(canonical_json(&json!([])), "[]");
}

#[test]
fn nested_sorts_only_objects_not_arrays() {
    // Arrays preserve insertion order; objects sort keys.
    let v = json!([{"b": 1, "a": 2}, {"z": 9}]);
    assert_eq!(canonical_json(&v), r#"[{"a":2,"b":1},{"z":9}]"#);
}

#[test]
fn deeply_nested_objects_sort_recursively() {
    let v = json!({"x": {"c": 1, "a": 2}});
    assert_eq!(canonical_json(&v), r#"{"x":{"a":2,"c":1}}"#);
}

#[test]
fn json_escape_uses_serde_rules() {
    // Backslash + quote are escaped; serde_json's default rules apply.
    let v = json!({"s": "a\"b\\c"});
    assert_eq!(canonical_json(&v), r#"{"s":"a\"b\\c"}"#);
}

#[test]
fn canonical_acceptance_attestation_payload() {
    let zeros = "0".repeat(64);
    let v = json!({
        "claim_id": "c1",
        "worker_id": "did:wcp:abc",
        "eta": "2026-06-01T10:00:00Z",
        "bid": null,
        "payload_hash": zeros,
        "signed_at": "2026-05-23T12:00:00Z",
    });
    let expected = format!(
        r#"{{"bid":null,"claim_id":"c1","eta":"2026-06-01T10:00:00Z","payload_hash":"{}","signed_at":"2026-05-23T12:00:00Z","worker_id":"did:wcp:abc"}}"#,
        "0".repeat(64)
    );
    assert_eq!(canonical_json(&v), expected);
}

#[test]
fn sha256_empty_vector() {
    assert_eq!(
        sha256_hex(b""),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
}

#[test]
fn sha256_abc_vector() {
    assert_eq!(
        sha256_hex(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
}

#[test]
fn sha256_long_vector() {
    // "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
    // is the canonical SHA-256 long test vector.
    assert_eq!(
        sha256_hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
    );
}
