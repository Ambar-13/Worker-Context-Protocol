//! Worker role: builder-pattern API.

use std::collections::HashMap;

use serde_json::{json, Value};

use crate::identity::WorkerIdentity;
use crate::rpc::{RpcClient, RpcError};
use crate::types::{AttestationMode, WorkerClass};

pub type Handler = Box<dyn Fn(Value) -> Value + Send + Sync>;

pub struct WorkerOptions {
    pub name: String,
    pub worker_class: WorkerClass,
    pub coordinator: String,
    pub principal_id: String,
    pub descriptor_types: Vec<String>,
}

pub struct Worker {
    pub options: WorkerOptions,
    identity: WorkerIdentity,
    rpc: Option<RpcClient>,
    handlers: HashMap<String, Handler>,
    attesters: HashMap<AttestationMode, Box<dyn Fn(String, Value) -> Value + Send + Sync>>,
}

pub struct WorkerBuilder {
    name: Option<String>,
    worker_class: Option<WorkerClass>,
    coordinator: Option<String>,
    principal_id: Option<String>,
    descriptor_types: Vec<String>,
}

impl Worker {
    pub fn builder() -> WorkerBuilder {
        WorkerBuilder {
            name: None,
            worker_class: None,
            coordinator: None,
            principal_id: None,
            descriptor_types: vec![],
        }
    }

    pub fn handle<F>(mut self, descriptor_type: &str, fn_: F) -> Self
    where
        F: Fn(Value) -> Value + Send + Sync + 'static,
    {
        self.handlers.insert(descriptor_type.to_string(), Box::new(fn_));
        self
    }

    pub fn attest<F>(mut self, mode: AttestationMode, fn_: F) -> Self
    where
        F: Fn(String, Value) -> Value + Send + Sync + 'static,
    {
        self.attesters.insert(mode, Box::new(fn_));
        self
    }

    pub async fn run(mut self) -> Result<(), RpcError> {
        self.rpc = Some(RpcClient::connect(&self.options.coordinator).await?);
        let descriptor = self.build_descriptor();
        let rpc = self.rpc.as_ref().unwrap();
        rpc.call(
            "capabilities/list",
            json!({"worker_id": self.identity.did, "capabilities": descriptor}),
        )
        .await?;
        Ok(())
    }

    fn build_descriptor(&self) -> Value {
        json!({
            "schema_version": "wcp/0.2",
            "worker_id": self.identity.did,
            "principal_id": self.options.principal_id,
            "class": self.options.worker_class.as_str(),
            "required": {
                "current_location": {"venue_id": "venue-a", "map_id": "map-a"},
                "available_windows": [{"rrule": "FREQ=DAILY", "timezone": "UTC"}],
                "attestation_methods_supported": [
                    "sensor-witness", "third-party-witness",
                    "cryptographic-presence", "owner-sign-off",
                ],
                "certifications": [],
                "policy_windows": [],
                "attestation_keys": [
                    {"kty": "OKP", "crv": "Ed25519", "x": self.identity.public_key_b64url}
                ],
                "as_of": chrono_now(),
            },
            "class_extension": {
                "descriptor_types": self.options.descriptor_types,
            },
        })
    }
}

impl WorkerBuilder {
    pub fn name(mut self, n: &str) -> Self {
        self.name = Some(n.into());
        self
    }
    pub fn worker_class(mut self, c: WorkerClass) -> Self {
        self.worker_class = Some(c);
        self
    }
    pub fn coordinator(mut self, c: &str) -> Self {
        self.coordinator = Some(c.into());
        self
    }
    pub fn principal_id(mut self, p: &str) -> Self {
        self.principal_id = Some(p.into());
        self
    }
    pub fn descriptor_type(mut self, d: &str) -> Self {
        self.descriptor_types.push(d.into());
        self
    }

    pub fn build(self) -> Result<Worker, &'static str> {
        Ok(Worker {
            options: WorkerOptions {
                name: self.name.ok_or("name is required")?,
                worker_class: self.worker_class.ok_or("worker_class is required")?,
                coordinator: self.coordinator.ok_or("coordinator is required")?,
                principal_id: self
                    .principal_id
                    .unwrap_or_else(|| "did:wcp:example-principal".to_string()),
                descriptor_types: self.descriptor_types,
            },
            identity: WorkerIdentity::generate(),
            rpc: None,
            handlers: HashMap::new(),
            attesters: HashMap::new(),
        })
    }
}

fn chrono_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    format!("{}.{:09}Z", now.as_secs(), now.subsec_nanos())
}
