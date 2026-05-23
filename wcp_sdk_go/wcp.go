// Package wcp is the Worker Context Protocol SDK for Go.
//
// Vendor-neutral. Designed for cloud-native coordinator integrators and
// infrastructure agents. Idiomatic Go: interfaces, contexts, channels for
// streams.
//
// Three roles: Worker, Agent, Coordinator. The Coordinator type is a
// registration index; the actual coordinator process is the reference Python
// implementation (wcp_coordinator) or any conformant alternative.
package wcp

const (
	// SchemaVersion is the WCP wire-protocol schema version this SDK targets.
	SchemaVersion = "wcp/0.2"
	// SdkVersion is this SDK's own version.
	SdkVersion = "0.95.0"
)

// WorkerClass enumerates the locked v0.2 worker class set.
type WorkerClass string

const (
	WorkerClassHuman             WorkerClass = "human"
	WorkerClassAutonomousRobot   WorkerClass = "autonomous_robot"
	WorkerClassTeleoperatedRobot WorkerClass = "teleoperated_robot"
	WorkerClassSemiAutonomous    WorkerClass = "semi_autonomous"
	WorkerClassHybrid            WorkerClass = "hybrid"
)

// AttestationMode enumerates the locked v0.2 attestation mode set.
type AttestationMode string

const (
	AttestationSensorWitness        AttestationMode = "sensor-witness"
	AttestationThirdPartyWitness    AttestationMode = "third-party-witness"
	AttestationCryptographicPres    AttestationMode = "cryptographic-presence"
	AttestationOwnerSignOff         AttestationMode = "owner-sign-off"
)

// AttestationEvidence is the shape a worker submits via tasks/attest.
type AttestationEvidence struct {
	SchemaVersion string                 `json:"schema_version"`
	Mode          AttestationMode        `json:"mode"`
	Kind          string                 `json:"kind"`
	Payload       map[string]interface{} `json:"payload"`
	PayloadHash   string                 `json:"payload_hash"`
	Sig           string                 `json:"sig"`
	WorkerID      string                 `json:"worker_id"`
	ClaimID       string                 `json:"claim_id"`
	CollectedAt   string                 `json:"collected_at"`
}
