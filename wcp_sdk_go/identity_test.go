package wcp

import (
	"encoding/base64"
	"strings"
	"testing"
)

func TestWorkerIdentity_GenerateHasWCPPrefix(t *testing.T) {
	id, err := NewWorkerIdentity()
	if err != nil {
		t.Fatalf("NewWorkerIdentity: %v", err)
	}
	if !strings.HasPrefix(id.DID, "did:wcp:") {
		t.Fatalf("DID should start with did:wcp:, got %q", id.DID)
	}
	suffix := strings.TrimPrefix(id.DID, "did:wcp:")
	if len(suffix) < 32 {
		t.Fatalf("DID suffix too short: %q", suffix)
	}
}

func TestAgentIdentity_GenerateHasWCPPrefix(t *testing.T) {
	id, err := NewAgentIdentity()
	if err != nil {
		t.Fatalf("NewAgentIdentity: %v", err)
	}
	if !strings.HasPrefix(id.DID, "did:wcp:") {
		t.Fatalf("got %q", id.DID)
	}
}

func TestIdentity_DistinctOnEachGenerate(t *testing.T) {
	a, _ := NewWorkerIdentity()
	b, _ := NewWorkerIdentity()
	if a.DID == b.DID {
		t.Fatalf("two generated DIDs collided: %q", a.DID)
	}
}

func TestIdentity_PublicKeyB64URLDecodesTo32Bytes(t *testing.T) {
	id, _ := NewWorkerIdentity()
	b, err := base64.RawURLEncoding.DecodeString(id.PublicKeyB64URL())
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(b) != 32 {
		t.Fatalf("Ed25519 pubkey must be 32 bytes, got %d", len(b))
	}
}

func TestIdentity_SignatureIsEd25519PrefixedURLSafe(t *testing.T) {
	id, _ := NewWorkerIdentity()
	sig, err := id.Sign(map[string]interface{}{"a": 1})
	if err != nil {
		t.Fatalf("sign: %v", err)
	}
	if !strings.HasPrefix(sig, "ed25519:") {
		t.Fatalf("sig should start with ed25519:, got %q", sig)
	}
	body := strings.TrimPrefix(sig, "ed25519:")
	b, err := base64.RawURLEncoding.DecodeString(body)
	if err != nil {
		t.Fatalf("sig body must decode as urlsafe-base64: %v", err)
	}
	if len(b) != 64 {
		t.Fatalf("Ed25519 sig must be 64 bytes, got %d", len(b))
	}
}

func TestIdentity_SignatureDeterministicForIdenticalCanonical(t *testing.T) {
	// Ed25519 is deterministic; canonical JSON ensures byte equality even
	// when input map iteration order differs.
	id, _ := NewWorkerIdentity()
	s1, _ := id.Sign(map[string]interface{}{"b": 2, "a": 1})
	s2, _ := id.Sign(map[string]interface{}{"a": 1, "b": 2})
	if s1 != s2 {
		t.Fatalf("expected determinism, got %q vs %q", s1, s2)
	}
}

func TestIdentity_SignatureDependsOnPayload(t *testing.T) {
	id, _ := NewWorkerIdentity()
	s1, _ := id.Sign(map[string]interface{}{"a": 1})
	s2, _ := id.Sign(map[string]interface{}{"a": 2})
	if s1 == s2 {
		t.Fatalf("expected different sigs for different payloads")
	}
}

func TestIdentity_AgentAndWorkerHaveDistinctKeys(t *testing.T) {
	w, _ := NewWorkerIdentity()
	a, _ := NewAgentIdentity()
	if w.DID == a.DID {
		t.Fatalf("worker and agent should not collide")
	}
	payload := map[string]interface{}{"task_id": "t1"}
	sw, _ := w.Sign(payload)
	sa, _ := a.Sign(payload)
	if sw == sa {
		t.Fatalf("sigs from different keys should differ")
	}
}
