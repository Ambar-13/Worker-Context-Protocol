// Package wcp: RobotAgent helper for the robot-as-agent pattern.
//
// An autonomous robot's onboard controller may act as a WCP agent, posting
// follow-up tasks to other workers (including other robots) from inside its
// own execute loop. The wire protocol is unchanged from v0.2; this type
// wraps the common "post a follow-up task that continues from a prior claim"
// case with a single method, PostContinuation.
//
// Spec: spec/0.95.md Sections 2 and 3.
// Pattern doc: docs/patterns/robot-as-agent.md.
// Reference deployment: examples/agents/delivery-robot-dispatcher/.
package wcp

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
)

// AgentClass enumerates the four agent_class values. Informational only;
// coordinators MUST NOT branch on it.
type AgentClass string

const (
	AgentClassLLM             AgentClass = "llm_agent"
	AgentClassEmbodied        AgentClass = "embodied_agent"
	AgentClassScheduled       AgentClass = "scheduled_agent"
	AgentClassHumanSupervisor AgentClass = "human_supervisor"
)

// RobotAgent is an Agent variant that declares an AgentClass and exposes a
// PostContinuation method for the robot-as-agent pattern.
type RobotAgent struct {
	*Agent
	AgentClass AgentClass
}

// NewRobotAgent dials the coordinator and returns a connected RobotAgent
// with the supplied agent_class. Defaults to AgentClassEmbodied.
func NewRobotAgent(ctx context.Context, coordinatorURL string, agentClass AgentClass) (*RobotAgent, error) {
	if agentClass == "" {
		agentClass = AgentClassEmbodied
	}
	switch agentClass {
	case AgentClassLLM, AgentClassEmbodied, AgentClassScheduled, AgentClassHumanSupervisor:
	default:
		return nil, fmt.Errorf("invalid agent_class: %s", agentClass)
	}
	a, err := NewAgent(ctx, coordinatorURL)
	if err != nil {
		return nil, err
	}
	return &RobotAgent{Agent: a, AgentClass: agentClass}, nil
}

// BuildContinuationArgs collects the application-layer blocks the caller
// must supply when building a continuation descriptor. v0.955: settlement
// is no longer a protocol concern; MaxAttestationAttempts and MarketplaceRef
// replace it.
type BuildContinuationArgs struct {
	PriorClaimID             string
	DescriptorType           string
	DescriptorPayload        map[string]interface{}
	RequiredEvidenceKinds    []string
	Constraints              map[string]interface{}
	AttestationRequirement   map[string]interface{}
	MaxAttestationAttempts   int
	MarketplaceRef           string
}

// BuildContinuation constructs a task descriptor that names a prior task via
// continuation_of. The caller MUST supply the two required application-layer
// blocks (constraints, attestation_requirement) per the v0.955 descriptor
// schema. MaxAttestationAttempts defaults to 1 if zero. MarketplaceRef is
// optional and opaque to WCP.
func (ra *RobotAgent) BuildContinuation(args BuildContinuationArgs) map[string]interface{} {
	kinds := args.RequiredEvidenceKinds
	if kinds == nil {
		kinds = []string{}
	}
	attempts := args.MaxAttestationAttempts
	if attempts == 0 {
		attempts = 1
	}
	descriptor := map[string]interface{}{
		"schema_version":     "wcp/0.2",
		"task_id":            newTaskID(),
		"posted_by":          ra.Identity.DID,
		"descriptor_type":    args.DescriptorType,
		"descriptor_payload": args.DescriptorPayload,
		"continuation_of": map[string]interface{}{
			"claim_id":                args.PriorClaimID,
			"required_evidence_kinds": kinds,
		},
		"constraints":              args.Constraints,
		"attestation_requirement":  args.AttestationRequirement,
		"max_attestation_attempts": attempts,
	}
	if args.MarketplaceRef != "" {
		descriptor["marketplace_ref"] = args.MarketplaceRef
	}
	return descriptor
}

// PostContinuation posts a follow-up task that continues from priorClaimID.
// Verifies the descriptor's continuation_of block matches before calling
// tasks/post.
func (ra *RobotAgent) PostContinuation(
	ctx context.Context,
	priorClaimID string,
	descriptor map[string]interface{},
	expiry string,
) (json.RawMessage, error) {
	cont, _ := descriptor["continuation_of"].(map[string]interface{})
	claimID, _ := cont["claim_id"].(string)
	if claimID != priorClaimID {
		return nil, fmt.Errorf("descriptor.continuation_of.claim_id (%q) does not match priorClaimID (%q)", claimID, priorClaimID)
	}
	return ra.PostTask(ctx, descriptor, expiry)
}

// AgentClassDeclaration returns the metadata block this agent advertises
// through its DID document's service array. Coordinators do not branch on it.
func (ra *RobotAgent) AgentClassDeclaration() map[string]interface{} {
	return map[string]interface{}{
		"type":           "WCPAgentClass",
		"agent_class":    string(ra.AgentClass),
		"advertised_at":  time.Now().UTC().Format(time.RFC3339),
	}
}

// newTaskID returns a UUID-like identifier. The SDK does not depend on a
// uuid package; this is enough entropy for task identifiers.
func newTaskID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	// RFC 4122 v4 marker bits
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	h := hex.EncodeToString(b[:])
	return fmt.Sprintf("%s-%s-%s-%s-%s", h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])
}
