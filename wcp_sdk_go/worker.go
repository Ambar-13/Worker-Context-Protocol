package wcp

import (
	"context"
	"encoding/json"
)

// Worker publishes capabilities and runs tasks dispatched by a coordinator.
type Worker struct {
	Identity *Identity
	Class    WorkerClass
	rpc      *RPCClient
}

// NewWorker dials the given coordinator and returns a Worker ready to publish
// its CapabilityDescriptor.
func NewWorker(ctx context.Context, class WorkerClass, coordinatorURL string) (*Worker, error) {
	id, err := NewWorkerIdentity()
	if err != nil {
		return nil, err
	}
	c, err := Dial(ctx, coordinatorURL)
	if err != nil {
		return nil, err
	}
	return &Worker{Identity: id, Class: class, rpc: c}, nil
}

// PublishCapabilities sends a capabilities/list call.
func (w *Worker) PublishCapabilities(
	ctx context.Context,
	descriptor map[string]interface{},
) (json.RawMessage, error) {
	return w.rpc.Call(ctx, "capabilities/list", map[string]interface{}{
		"worker_id":    w.Identity.DID,
		"capabilities": descriptor,
	})
}

// Close releases the connection.
func (w *Worker) Close() error { return w.rpc.Close() }
