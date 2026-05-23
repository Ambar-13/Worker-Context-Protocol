package wcp

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"

	"github.com/gorilla/websocket"
)

// RPCError is a JSON-RPC 2.0 error returned by a WCP coordinator.
type RPCError struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data,omitempty"`
}

func (e *RPCError) Error() string {
	return fmt.Sprintf("wcp rpc error code=%d: %s", e.Code, e.Message)
}

// RPCClient is a minimal JSON-RPC 2.0 client over WebSocket.
type RPCClient struct {
	conn    *websocket.Conn
	mu      sync.Mutex
	nextID  uint64
	pending sync.Map // id -> chan rpcResponse
	closed  atomic.Bool
}

type rpcResponse struct {
	Result json.RawMessage
	Err    *RPCError
}

type rpcEnvelope struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      uint64          `json:"id"`
	Method  string          `json:"method"`
	Params  interface{}     `json:"params"`
}

type rpcReply struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      uint64          `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// Dial connects to a WCP coordinator WebSocket URL.
func Dial(ctx context.Context, url string) (*RPCClient, error) {
	conn, _, err := websocket.DefaultDialer.DialContext(ctx, url, nil)
	if err != nil {
		return nil, fmt.Errorf("wcp dial: %w", err)
	}
	c := &RPCClient{conn: conn}
	go c.readLoop()
	return c, nil
}

func (c *RPCClient) readLoop() {
	for !c.closed.Load() {
		_, msg, err := c.conn.ReadMessage()
		if err != nil {
			return
		}
		var reply rpcReply
		if err := json.Unmarshal(msg, &reply); err != nil {
			continue
		}
		if ch, ok := c.pending.LoadAndDelete(reply.ID); ok {
			ch.(chan rpcResponse) <- rpcResponse{Result: reply.Result, Err: reply.Error}
		}
	}
}

// Call sends a JSON-RPC request and awaits a response.
func (c *RPCClient) Call(ctx context.Context, method string, params interface{}) (json.RawMessage, error) {
	id := atomic.AddUint64(&c.nextID, 1)
	ch := make(chan rpcResponse, 1)
	c.pending.Store(id, ch)
	defer c.pending.Delete(id)

	envelope := rpcEnvelope{JSONRPC: "2.0", ID: id, Method: method, Params: params}
	c.mu.Lock()
	err := c.conn.WriteJSON(envelope)
	c.mu.Unlock()
	if err != nil {
		return nil, err
	}
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case resp := <-ch:
		if resp.Err != nil {
			return nil, resp.Err
		}
		return resp.Result, nil
	}
}

// Close shuts down the connection.
func (c *RPCClient) Close() error {
	c.closed.Store(true)
	return c.conn.Close()
}

// Common predicate to check if a Go error is an *RPCError.
func IsRPCError(err error) (*RPCError, bool) {
	var rpcErr *RPCError
	if errors.As(err, &rpcErr) {
		return rpcErr, true
	}
	return nil, false
}
