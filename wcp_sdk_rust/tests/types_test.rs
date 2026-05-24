//! Typed enums serialize / deserialize to the strings spec/0.955.md uses.

use serde_json::json;
use wcp_sdk::types::{AttestationMode, WorkerClass};

#[test]
fn worker_class_string_values_match_spec() {
    assert_eq!(WorkerClass::Human.as_str(), "human");
    assert_eq!(WorkerClass::AutonomousRobot.as_str(), "autonomous_robot");
    assert_eq!(WorkerClass::TeleoperatedRobot.as_str(), "teleoperated_robot");
    assert_eq!(WorkerClass::SemiAutonomous.as_str(), "semi_autonomous");
    assert_eq!(WorkerClass::Hybrid.as_str(), "hybrid");
}

#[test]
fn worker_class_serializes_to_snake_case() {
    let v = serde_json::to_value(WorkerClass::AutonomousRobot).unwrap();
    assert_eq!(v, json!("autonomous_robot"));
}

#[test]
fn worker_class_round_trips() {
    let v = json!("hybrid");
    let parsed: WorkerClass = serde_json::from_value(v).unwrap();
    assert_eq!(parsed, WorkerClass::Hybrid);
}

#[test]
fn attestation_mode_string_values_match_spec() {
    assert_eq!(AttestationMode::SensorWitness.as_str(), "sensor-witness");
    assert_eq!(AttestationMode::ThirdPartyWitness.as_str(), "third-party-witness");
    assert_eq!(AttestationMode::CryptographicPresence.as_str(), "cryptographic-presence");
    assert_eq!(AttestationMode::OwnerSignOff.as_str(), "owner-sign-off");
}

#[test]
fn attestation_mode_serializes_with_hyphens() {
    let v = serde_json::to_value(AttestationMode::OwnerSignOff).unwrap();
    assert_eq!(v, json!("owner-sign-off"));
}

#[test]
fn attestation_mode_round_trips_all_variants() {
    for m in [
        AttestationMode::SensorWitness,
        AttestationMode::ThirdPartyWitness,
        AttestationMode::CryptographicPresence,
        AttestationMode::OwnerSignOff,
    ] {
        let v = serde_json::to_value(m).unwrap();
        let parsed: AttestationMode = serde_json::from_value(v).unwrap();
        assert_eq!(parsed, m);
    }
}

#[test]
fn worker_class_unknown_variant_fails_cleanly() {
    let v = json!("emperor");
    let parsed: Result<WorkerClass, _> = serde_json::from_value(v);
    assert!(parsed.is_err());
}

#[test]
fn attestation_mode_unknown_variant_fails_cleanly() {
    let v = json!("smell-witness");
    let parsed: Result<AttestationMode, _> = serde_json::from_value(v);
    assert!(parsed.is_err());
}
