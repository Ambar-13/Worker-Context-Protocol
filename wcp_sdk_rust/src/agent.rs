//! Agent role: builder-pattern API.

use serde_json::{json, Value};

use crate::identity::AgentIdentity;
use crate::rpc::{RpcClient, RpcError};

pub struct AgentOptions {
    pub name: String,
    pub coordinator: String,
}

pub struct Agent {
    pub options: AgentOptions,
    pub identity: AgentIdentity,
    rpc: Option<RpcClient>,
}

impl Agent {
    pub fn builder() -> AgentBuilder {
        AgentBuilder {
            name: None,
            coordinator: None,
        }
    }

    pub async fn connect(&mut self) -> Result<(), RpcError> {
        self.rpc = Some(RpcClient::connect(&self.options.coordinator).await?);
        Ok(())
    }

    pub async fn post_task(
        &self,
        task: Value,
        bond_ref: &str,
        expiry: &str,
    ) -> Result<Value, RpcError> {
        let rpc = self.rpc.as_ref().ok_or_else(|| {
            RpcError::Internal("connect() must be called first".into())
        })?;
        rpc.call(
            "tasks/post",
            json!({
                "task": task,
                "bond_ref": bond_ref,
                "expiry": expiry,
            }),
        )
        .await
    }

    pub async fn discover_capabilities(&self, filter: Value) -> Result<Value, RpcError> {
        let rpc = self.rpc.as_ref().ok_or_else(|| {
            RpcError::Internal("connect() must be called first".into())
        })?;
        rpc.call(
            "capabilities/subscribe",
            json!({"agent_did": self.identity.did, "filter": filter}),
        )
        .await
    }
}

pub struct AgentBuilder {
    name: Option<String>,
    coordinator: Option<String>,
}

impl AgentBuilder {
    pub fn name(mut self, n: &str) -> Self {
        self.name = Some(n.into());
        self
    }
    pub fn coordinator(mut self, c: &str) -> Self {
        self.coordinator = Some(c.into());
        self
    }
    pub fn build(self) -> Result<Agent, &'static str> {
        Ok(Agent {
            options: AgentOptions {
                name: self.name.ok_or("name is required")?,
                coordinator: self.coordinator.ok_or("coordinator is required")?,
            },
            identity: AgentIdentity::generate(),
            rpc: None,
        })
    }
}
