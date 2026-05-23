//! WCP typed objects compatible across language SDKs.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum WorkerClass {
    Human,
    AutonomousRobot,
    TeleoperatedRobot,
    SemiAutonomous,
    Hybrid,
}

impl WorkerClass {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Human => "human",
            Self::AutonomousRobot => "autonomous_robot",
            Self::TeleoperatedRobot => "teleoperated_robot",
            Self::SemiAutonomous => "semi_autonomous",
            Self::Hybrid => "hybrid",
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum AttestationMode {
    #[serde(rename = "sensor-witness")]
    SensorWitness,
    #[serde(rename = "third-party-witness")]
    ThirdPartyWitness,
    #[serde(rename = "cryptographic-presence")]
    CryptographicPresence,
    #[serde(rename = "owner-sign-off")]
    OwnerSignOff,
}

impl AttestationMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::SensorWitness => "sensor-witness",
            Self::ThirdPartyWitness => "third-party-witness",
            Self::CryptographicPresence => "cryptographic-presence",
            Self::OwnerSignOff => "owner-sign-off",
        }
    }
}
