//! WCP SDK for Rust (v1.0-rc2).
//!
//! Vendor-neutral. For embedded workers (drones, AMRs, sensor nodes,
//! industrial controllers) and cloud coordinator integrators.
//!
//! # Example
//!
//! ```no_run
//! use wcp_sdk::{Worker, WorkerOptions, WorkerClass};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let worker = Worker::builder()
//!         .name("amr-7")
//!         .worker_class(WorkerClass::AutonomousRobot)
//!         .coordinator("ws://localhost:8000/wcp/ws")
//!         .build()?;
//!     worker.run().await?;
//!     Ok(())
//! }
//! ```

pub mod canonical;
pub mod identity;
pub mod rpc;
pub mod types;
pub mod worker;
pub mod agent;

pub use agent::{Agent, AgentOptions};
pub use identity::{AgentIdentity, WorkerIdentity};
pub use rpc::{RpcClient, RpcError};
pub use types::{AttestationMode, WorkerClass};
pub use worker::{Worker, WorkerOptions};

pub const SCHEMA_VERSION: &str = "wcp/1.0-rc1";
pub const SDK_VERSION: &str = "1.0.0-rc2";
