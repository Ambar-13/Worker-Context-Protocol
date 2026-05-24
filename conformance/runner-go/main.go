// wcp-conformance-go: a second-language runner for the WCP conformance
// bundle. Loads conformance/test-suite/level<N>.json, materializes
// {{key}} substitutions (with fresh {{uuid}} per site), opens a
// JSON-RPC 2.0 WebSocket to the target, runs each case, and reports
// PASS / FAIL.
//
// Usage:
//
//	wcp-conformance-go --target ws://localhost:9300/wcp/ws --level 1
//
// The Python runner remains the reference. This Go implementation
// exists to shake out implicit Python-isms in the test bundle and to
// satisfy the four-language SDK symmetry claim at the conformance
// level. The Level 1 cases are covered; Level 2 and Level 3 cases that
// require multi-step flow support are reported as SKIP for now.
package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"net/url"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
	guid "crypto/rand"
)

type testBundle struct {
	SchemaVersion string     `json:"schema_version"`
	Level         int        `json:"level"`
	Cases         []testCase `json:"cases"`
}

type testCase struct {
	ID             string                 `json:"id"`
	Level          int                    `json:"level"`
	Method         string                 `json:"method"`
	ParamsTemplate map[string]interface{} `json:"params_template"`
	Expected       map[string]interface{} `json:"expected"`
	SetupFixtures  []interface{}          `json:"setup_fixtures,omitempty"`
}

type testResult struct {
	ID     string
	Passed bool
	Reason string
}

func main() {
	target := flag.String("target", "", "target wss:// URL")
	level := flag.Int("level", 1, "conformance level (1|2|3)")
	bundleDir := flag.String("bundle-dir", "../test-suite", "test suite directory")
	flag.Parse()
	if *target == "" {
		fmt.Fprintln(os.Stderr, "--target required")
		os.Exit(2)
	}
	if *level < 1 || *level > 3 {
		fmt.Fprintln(os.Stderr, "--level must be 1, 2, or 3")
		os.Exit(2)
	}
	bundlePath := fmt.Sprintf("%s/level%d.json", *bundleDir, *level)
	raw, err := os.ReadFile(bundlePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read bundle: %v\n", err)
		os.Exit(2)
	}
	var bundle testBundle
	if err := json.Unmarshal(raw, &bundle); err != nil {
		fmt.Fprintf(os.Stderr, "parse bundle: %v\n", err)
		os.Exit(2)
	}

	client, err := dial(*target)
	if err != nil {
		fmt.Fprintf(os.Stderr, "dial: %v\n", err)
		os.Exit(1)
	}
	defer client.Close()

	ctx := buildContext()

	pass, fail, skip := 0, 0, 0
	for _, c := range bundle.Cases {
		if c.Level > *level {
			continue
		}
		r := runCase(client, c, ctx)
		switch {
		case r.Passed:
			pass++
			fmt.Printf("PASS  %s\n", r.ID)
		case strings.HasPrefix(r.Reason, "SKIP:"):
			skip++
			fmt.Printf("SKIP  %s  (%s)\n", r.ID, r.Reason)
		default:
			fail++
			fmt.Printf("FAIL  %s  reason=%s\n", r.ID, r.Reason)
		}
	}
	fmt.Printf("\nLevel %d: %d pass / %d fail / %d skip\n", *level, pass, fail, skip)
	if fail > 0 {
		os.Exit(1)
	}
}

// buildContext mints fresh per-run DIDs and seed values for {{key}}
// substitution. {{uuid}} is special-cased per substitution site below.
func buildContext() map[string]string {
	workerDID := genDIDWithPub()
	agentDID := genDIDWithPub()
	return map[string]string{
		"worker_did":     workerDID.did,
		"agent_did":      agentDID.did,
		"schema_version": "wcp/0.2",
		"now_iso":        time.Now().UTC().Format(time.RFC3339),
	}
}

type didKeyPair struct {
	did     string
	privKey ed25519.PrivateKey
	pubKey  ed25519.PublicKey
}

func genDIDWithPub() didKeyPair {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	return didKeyPair{
		did:     "did:wcp:" + base58Encode(pub),
		privKey: priv,
		pubKey:  pub,
	}
}

const b58Alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

func base58Encode(b []byte) string {
	src := append([]byte(nil), b...)
	leading := 0
	for _, x := range src {
		if x == 0 {
			leading++
		} else {
			break
		}
	}
	var digits []byte
	for {
		isZero := true
		rem := 0
		for i := 0; i < len(src); i++ {
			carry := int(src[i]) + rem*256
			src[i] = byte(carry / 58)
			rem = carry % 58
			if src[i] != 0 {
				isZero = false
			}
		}
		digits = append([]byte{b58Alphabet[rem]}, digits...)
		if isZero {
			break
		}
	}
	out := make([]byte, leading+len(digits))
	for i := 0; i < leading; i++ {
		out[i] = '1'
	}
	copy(out[leading:], digits)
	return string(out)
}

// freshUUID returns an RFC 4122 v4-ish identifier built from /dev/urandom.
func freshUUID() string {
	b := make([]byte, 16)
	_, _ = guid.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf(
		"%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:16],
	)
}

// substitute walks the params template and replaces {{key}} tokens.
// {{uuid}} produces a fresh uuid per substitution site so multiple
// uses inside one case do not collide.
func substitute(v interface{}, ctx map[string]string) interface{} {
	switch x := v.(type) {
	case string:
		if strings.HasPrefix(x, "{{") && strings.HasSuffix(x, "}}") {
			key := strings.TrimSpace(x[2 : len(x)-2])
			if key == "uuid" {
				return freshUUID()
			}
			if val, ok := ctx[key]; ok {
				return val
			}
			return x
		}
		// inline {{uuid}}
		if strings.Contains(x, "{{uuid}}") {
			out := strings.Builder{}
			for {
				i := strings.Index(x, "{{uuid}}")
				if i == -1 {
					out.WriteString(x)
					break
				}
				out.WriteString(x[:i])
				out.WriteString(freshUUID())
				x = x[i+len("{{uuid}}"):]
			}
			return out.String()
		}
		return x
	case map[string]interface{}:
		out := make(map[string]interface{}, len(x))
		for k, vv := range x {
			out[k] = substitute(vv, ctx)
		}
		return out
	case []interface{}:
		out := make([]interface{}, len(x))
		for i, vv := range x {
			out[i] = substitute(vv, ctx)
		}
		return out
	default:
		return v
	}
}

// runCase issues the case's method call and validates against the
// expected block. Cases needing multi-step setup are SKIPped here;
// they will be implemented when the Go runner extends to flows.
func runCase(c *rpcClient, tc testCase, ctx map[string]string) testResult {
	if len(tc.SetupFixtures) > 0 {
		return testResult{ID: tc.ID, Passed: false, Reason: "SKIP: setup_fixtures not yet implemented in Go runner"}
	}
	params, _ := substitute(tc.ParamsTemplate, ctx).(map[string]interface{})

	resp, rpcErr := c.call(tc.Method, params)
	return checkExpected(tc, resp, rpcErr)
}

func checkExpected(tc testCase, resp map[string]interface{}, rpcErr *rpcErrorObject) testResult {
	if tc.Expected == nil {
		return testResult{ID: tc.ID, Passed: false, Reason: "no expected criterion defined"}
	}
	if want, ok := tc.Expected["error_code"]; ok {
		wantCode := int(toFloat(want))
		if rpcErr == nil {
			return testResult{ID: tc.ID, Passed: false, Reason: fmt.Sprintf("expected error code %d, got success", wantCode)}
		}
		if rpcErr.Code != wantCode {
			return testResult{ID: tc.ID, Passed: false, Reason: fmt.Sprintf("expected error code %d, got %d", wantCode, rpcErr.Code)}
		}
		return testResult{ID: tc.ID, Passed: true}
	}
	if want, ok := tc.Expected["result_keys"]; ok {
		if rpcErr != nil {
			return testResult{ID: tc.ID, Passed: false, Reason: fmt.Sprintf("expected result keys, got error code %d: %s", rpcErr.Code, rpcErr.Message)}
		}
		needed, _ := want.([]interface{})
		for _, k := range needed {
			key, _ := k.(string)
			if _, present := resp[key]; !present {
				return testResult{ID: tc.ID, Passed: false, Reason: fmt.Sprintf("missing result key: %q", key)}
			}
		}
		return testResult{ID: tc.ID, Passed: true}
	}
	return testResult{ID: tc.ID, Passed: false, Reason: "SKIP: criterion shape not yet supported by Go runner (verifier_decision, audit_entries_contain, property_holds, etc.)"}
}

func toFloat(v interface{}) float64 {
	switch x := v.(type) {
	case float64:
		return x
	case int:
		return float64(x)
	case json.Number:
		f, _ := x.Float64()
		return f
	}
	return 0
}

// --- minimal JSON-RPC 2.0 WebSocket client ---------------------------------

type rpcClient struct {
	conn    *websocket.Conn
	nextID  uint64
	mu      sync.Mutex
	pending sync.Map // id -> chan response
}

type response struct {
	Result map[string]interface{}
	Err    *rpcErrorObject
}

type rpcErrorObject struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func dial(target string) (*rpcClient, error) {
	u, err := url.Parse(target)
	if err != nil {
		return nil, err
	}
	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return nil, err
	}
	c := &rpcClient{conn: conn}
	go c.reader()
	return c, nil
}

func (c *rpcClient) Close() {
	if c.conn != nil {
		_ = c.conn.Close()
	}
}

func (c *rpcClient) reader() {
	for {
		_, msg, err := c.conn.ReadMessage()
		if err != nil {
			return
		}
		var env struct {
			ID     uint64                 `json:"id"`
			Result map[string]interface{} `json:"result"`
			Error  *rpcErrorObject        `json:"error"`
		}
		if err := json.Unmarshal(msg, &env); err != nil {
			continue
		}
		if ch, ok := c.pending.LoadAndDelete(env.ID); ok {
			ch.(chan response) <- response{Result: env.Result, Err: env.Error}
		}
	}
}

func (c *rpcClient) call(method string, params map[string]interface{}) (map[string]interface{}, *rpcErrorObject) {
	id := atomic.AddUint64(&c.nextID, 1)
	ch := make(chan response, 1)
	c.pending.Store(id, ch)
	req := map[string]interface{}{
		"jsonrpc": "2.0",
		"id":      id,
		"method":  method,
		"params":  params,
	}
	c.mu.Lock()
	err := c.conn.WriteJSON(req)
	c.mu.Unlock()
	if err != nil {
		c.pending.Delete(id)
		return nil, &rpcErrorObject{Code: -32603, Message: err.Error()}
	}
	select {
	case r := <-ch:
		return r.Result, r.Err
	case <-time.After(5 * time.Second):
		c.pending.Delete(id)
		return nil, &rpcErrorObject{Code: -32603, Message: "timeout"}
	}
}

// silence unused-import warnings for builds where reflect is dropped.
var _ = base64.StdEncoding
