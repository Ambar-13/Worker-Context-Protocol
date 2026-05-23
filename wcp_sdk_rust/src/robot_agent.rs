//! RobotAgent: convenience wrapper around `Agent` for the robot-as-agent
//! pattern (an autonomous robot's onboard controller acting as a WCP agent
//! and posting follow-up tasks from inside its execute loop).
//!
//! Spec: `spec/0.95.md` Sections 2 and 3 (continuation pattern), amended
//! by `spec/0.955.md` (settlement removed from descriptor;
//! `max_attestation_attempts` and `marketplace_ref` added).
//! Pattern doc: `docs/patterns/robot-as-agent.md`.
//!
//! Example:
//!
//! ```no_run
//! use wcp_sdk::{RobotAgent, AgentClass};
//! use serde_json::json;
//!
//! # async fn main_inner() -> Result<(), Box<dyn std::error::Error>> {
//! let mut robot = RobotAgent::builder()
//!     .name("amr-onboard-planner")
//!     .coordinator("ws://localhost:8000/wcp/ws")
//!     .agent_class(AgentClass::EmbodiedAgent)
//!     .build()?;
//! robot.connect().await?;
//!
//! let descriptor = robot.build_continuation(
//!     "claim-abc-123",
//!     "place_on_shelf",
//!     json!({ "shelf_id": "WS-7-A" }),
//!     vec!["indoor_pose_track".into()],
//!     json!({}),                              // constraints
//!     json!({ "modes": ["sensor-witness"],    // attestation_requirement
//!             "threshold": "any",
//!             "evidence_schema": [
//!               { "mode": "sensor-witness", "kinds": ["weight_delta"] }
//!             ]}),
//!     1,                                       // max_attestation_attempts
//!     None,                                    // marketplace_ref
//! );
//! robot.post_continuation("claim-abc-123", &descriptor, "2026-12-31T00:00:00Z").await?;
//! # Ok(()) }
//! ```

use serde_json::{json, Value};
use uuid::Uuid;

use crate::agent::Agent;
use crate::rpc::RpcError;

/// Informational. Coordinators MUST NOT branch on this value; operators MAY
/// use it for filtering, accounting, and federation-trust-anchor scope.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgentClass {
    LlmAgent,
    EmbodiedAgent,
    ScheduledAgent,
    HumanSupervisor,
}

impl AgentClass {
    pub fn as_str(self) -> &'static str {
        match self {
            AgentClass::LlmAgent => "llm_agent",
            AgentClass::EmbodiedAgent => "embodied_agent",
            AgentClass::ScheduledAgent => "scheduled_agent",
            AgentClass::HumanSupervisor => "human_supervisor",
        }
    }
}

pub struct RobotAgent {
    inner: Agent,
    agent_class: AgentClass,
}

pub struct RobotAgentBuilder {
    name: Option<String>,
    coordinator: Option<String>,
    agent_class: AgentClass,
}

impl RobotAgent {
    pub fn builder() -> RobotAgentBuilder {
        RobotAgentBuilder {
            name: None,
            coordinator: None,
            agent_class: AgentClass::EmbodiedAgent,
        }
    }

    pub fn agent_class(&self) -> AgentClass {
        self.agent_class
    }

    pub fn did(&self) -> &str {
        &self.inner.identity.did
    }

    pub async fn connect(&mut self) -> Result<(), RpcError> {
        self.inner.connect().await
    }

    /// Build a task descriptor that names a prior task via `continuation_of`.
    /// The caller supplies the two required application-layer blocks
    /// (constraints, attestation_requirement). v0.955 settlement is no longer
    /// a protocol concern; pass `marketplace_ref` to correlate with an
    /// external settlement-layer record.
    #[allow(clippy::too_many_arguments)]
    pub fn build_continuation(
        &self,
        prior_claim_id: &str,
        descriptor_type: &str,
        descriptor_payload: Value,
        required_evidence_kinds: Vec<String>,
        constraints: Value,
        attestation_requirement: Value,
        max_attestation_attempts: u32,
        marketplace_ref: Option<&str>,
    ) -> Value {
        let mut descriptor = json!({
            "schema_version": "wcp/0.2",
            "task_id": Uuid::new_v4().to_string(),
            "posted_by": self.did(),
            "descriptor_type": descriptor_type,
            "descriptor_payload": descriptor_payload,
            "continuation_of": {
                "claim_id": prior_claim_id,
                "required_evidence_kinds": required_evidence_kinds,
            },
            "constraints": constraints,
            "attestation_requirement": attestation_requirement,
            "max_attestation_attempts": max_attestation_attempts,
        });
        if let Some(mref) = marketplace_ref {
            descriptor["marketplace_ref"] = json!(mref);
        }
        descriptor
    }

    /// Post a follow-up task that continues from `prior_claim_id`. Verifies
    /// that the descriptor's continuation_of block matches before calling
    /// tasks/post.
    pub async fn post_continuation(
        &self,
        prior_claim_id: &str,
        descriptor: &Value,
        expiry: &str,
    ) -> Result<Value, RpcError> {
        let cont_claim = descriptor
            .get("continuation_of")
            .and_then(|c| c.get("claim_id"))
            .and_then(|v| v.as_str());
        if cont_claim != Some(prior_claim_id) {
            return Err(RpcError::Internal(
                "descriptor.continuation_of.claim_id does not match prior_claim_id"
                    .into(),
            ));
        }
        self.inner
            .post_task(descriptor.clone(), expiry)
            .await
    }

    /// The agent_class metadata block this agent advertises through its DID
    /// document's service array.
    pub fn agent_class_declaration(&self) -> Value {
        json!({
            "type": "WCPAgentClass",
            "agent_class": self.agent_class.as_str(),
        })
    }
}

impl RobotAgentBuilder {
    pub fn name(mut self, name: impl Into<String>) -> Self {
        self.name = Some(name.into());
        self
    }

    pub fn coordinator(mut self, coordinator: impl Into<String>) -> Self {
        self.coordinator = Some(coordinator.into());
        self
    }

    pub fn agent_class(mut self, class: AgentClass) -> Self {
        self.agent_class = class;
        self
    }

    pub fn build(self) -> Result<RobotAgent, &'static str> {
        let name = self.name.ok_or("name is required")?;
        let coordinator = self.coordinator.ok_or("coordinator is required")?;
        let inner = Agent::builder()
            .name(&name)
            .coordinator(&coordinator)
            .build()?;
        Ok(RobotAgent {
            inner,
            agent_class: self.agent_class,
        })
    }
}
