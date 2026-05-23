//! did:wcp identity primitives.

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use rand_core::OsRng;

use crate::canonical::canonical_json;
use serde_json::Value;

pub struct WorkerIdentity {
    signing_key: SigningKey,
    pub did: String,
    pub public_key_b64url: String,
}

impl WorkerIdentity {
    pub fn generate() -> Self {
        let signing_key = SigningKey::generate(&mut OsRng);
        let verifying_key: VerifyingKey = signing_key.verifying_key();
        let pub_bytes = verifying_key.to_bytes();
        let did = format!("did:wcp:{}", bs58::encode(pub_bytes).into_string());
        let public_key_b64url = URL_SAFE_NO_PAD.encode(pub_bytes);
        WorkerIdentity {
            signing_key,
            did,
            public_key_b64url,
        }
    }

    pub fn sign(&self, payload: &Value) -> String {
        let bytes = canonical_json(payload);
        let sig: Signature = self.signing_key.sign(bytes.as_bytes());
        format!("ed25519:{}", URL_SAFE_NO_PAD.encode(sig.to_bytes()))
    }
}

pub struct AgentIdentity {
    signing_key: SigningKey,
    pub did: String,
}

impl AgentIdentity {
    pub fn generate() -> Self {
        let signing_key = SigningKey::generate(&mut OsRng);
        let verifying_key: VerifyingKey = signing_key.verifying_key();
        let pub_bytes = verifying_key.to_bytes();
        let did = format!("did:wcp:{}", bs58::encode(pub_bytes).into_string());
        AgentIdentity { signing_key, did }
    }

    pub fn sign(&self, payload: &Value) -> String {
        let bytes = canonical_json(payload);
        let sig: Signature = self.signing_key.sign(bytes.as_bytes());
        format!("ed25519:{}", URL_SAFE_NO_PAD.encode(sig.to_bytes()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn worker_did_format() {
        let w = WorkerIdentity::generate();
        assert!(w.did.starts_with("did:wcp:"));
    }

    #[test]
    fn signature_format() {
        let w = WorkerIdentity::generate();
        let sig = w.sign(&json!({"task_id": "t1"}));
        assert!(sig.starts_with("ed25519:"));
    }
}
