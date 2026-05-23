//! Canonical JSON compatible with the Python and TypeScript SDKs.
//!
//! Sorted keys, no whitespace; matches `json.dumps(payload, sort_keys=True,
//! separators=(",", ":"))`.

use serde_json::{Map, Value};

pub fn canonical_json(value: &Value) -> String {
    match value {
        Value::Null => "null".into(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => n.to_string(),
        Value::String(s) => json_escape(s),
        Value::Array(arr) => {
            let mut out = String::from("[");
            for (i, v) in arr.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push_str(&canonical_json(v));
            }
            out.push(']');
            out
        }
        Value::Object(obj) => canonical_object(obj),
    }
}

fn canonical_object(obj: &Map<String, Value>) -> String {
    let mut keys: Vec<&String> = obj.keys().collect();
    keys.sort();
    let mut out = String::from("{");
    for (i, k) in keys.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        out.push_str(&json_escape(k));
        out.push(':');
        out.push_str(&canonical_json(&obj[*k]));
    }
    out.push('}');
    out
}

fn json_escape(s: &str) -> String {
    serde_json::to_string(s).unwrap_or_else(|_| String::new())
}

pub fn sha256_hex(data: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(data);
    let out = h.finalize();
    hex(&out)
}

fn hex(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push_str(&format!("{:02x}", b));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn sorts_keys() {
        let v = json!({"b": 1, "a": 2});
        assert_eq!(canonical_json(&v), r#"{"a":2,"b":1}"#);
    }

    #[test]
    fn matches_known_canonical_payload() {
        let v = json!({
            "claim_id": "c1",
            "worker_id": "did:wcp:abc",
            "eta": "2026-06-01T10:00:00Z",
            "bid": null,
            "payload_hash": "0".repeat(64),
            "signed_at": "2026-05-23T12:00:00Z"
        });
        let s = canonical_json(&v);
        assert!(s.contains(r#""bid":null"#));
        assert!(s.starts_with(r#"{"bid":null,"claim_id":"#));
    }

    #[test]
    fn sha_known_vector() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }
}
