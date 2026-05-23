package wcp

import (
	"context"
	"encoding/json"
)

// Agent posts tasks and discovers capabilities.
type Agent struct {
	Identity *Identity
	rpc      *RPCClient
}

// NewAgent dials the given coordinator and returns a connected Agent.
func NewAgent(ctx context.Context, coordinatorURL string) (*Agent, error) {
	id, err := NewAgentIdentity()
	if err != nil {
		return nil, err
	}
	c, err := Dial(ctx, coordinatorURL)
	if err != nil {
		return nil, err
	}
	return &Agent{Identity: id, rpc: c}, nil
}

// PostTask posts a TaskDescriptor. v0.955: bond_ref is no longer part of the
// envelope (settlement is not a protocol concern). External settlement
// correlation lives in task["accounting_ref"] if needed.
func (a *Agent) PostTask(
	ctx context.Context,
	task map[string]interface{},
	expiry string,
) (json.RawMessage, error) {
	return a.rpc.Call(ctx, "tasks/post", map[string]interface{}{
		"task":   task,
		"expiry": expiry,
	})
}

// DiscoverCapabilities subscribes to capability updates filtered by `filter`.
func (a *Agent) DiscoverCapabilities(
	ctx context.Context,
	filter map[string]interface{},
) (json.RawMessage, error) {
	return a.rpc.Call(ctx, "capabilities/subscribe", map[string]interface{}{
		"agent_did": a.Identity.DID,
		"filter":    filter,
	})
}

// Close releases the connection.
func (a *Agent) Close() error { return a.rpc.Close() }
