package wcp

import (
	"strings"
	"testing"
)

func TestCanonicalJSON_Primitives(t *testing.T) {
	cases := []struct {
		name string
		in   interface{}
		want string
	}{
		{"null", nil, "null"},
		{"bool true", true, "true"},
		{"bool false", false, "false"},
		{"int", 42, "42"},
		{"int negative", -7, "-7"},
		{"string", "hello", `"hello"`},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			b, err := CanonicalJSON(c.in)
			if err != nil {
				t.Fatalf("err: %v", err)
			}
			if string(b) != c.want {
				t.Fatalf("got %q want %q", string(b), c.want)
			}
		})
	}
}

func TestCanonicalJSON_EmptyContainers(t *testing.T) {
	b, _ := CanonicalJSON(map[string]interface{}{})
	if string(b) != "{}" {
		t.Fatalf("empty obj: got %q", string(b))
	}
	b, _ = CanonicalJSON([]interface{}{})
	if string(b) != "[]" {
		t.Fatalf("empty arr: got %q", string(b))
	}
}

func TestCanonicalJSON_SortsObjectKeysOnly(t *testing.T) {
	in := []interface{}{
		map[string]interface{}{"b": 1.0, "a": 2.0},
		map[string]interface{}{"z": 9.0},
	}
	b, err := CanonicalJSON(in)
	if err != nil {
		t.Fatalf("err: %v", err)
	}
	want := `[{"a":2,"b":1},{"z":9}]`
	if string(b) != want {
		t.Fatalf("got %q want %q", string(b), want)
	}
}

func TestCanonicalJSON_NestedSorts(t *testing.T) {
	in := map[string]interface{}{
		"x": map[string]interface{}{"c": 1.0, "a": 2.0},
	}
	b, _ := CanonicalJSON(in)
	want := `{"x":{"a":2,"c":1}}`
	if string(b) != want {
		t.Fatalf("got %q want %q", string(b), want)
	}
}

func TestCanonicalJSON_AcceptanceAttestationVector(t *testing.T) {
	in := map[string]interface{}{
		"claim_id":     "c1",
		"worker_id":    "did:wcp:abc",
		"eta":          "2026-06-01T10:00:00Z",
		"bid":          nil,
		"payload_hash": strings.Repeat("0", 64),
		"signed_at":    "2026-05-23T12:00:00Z",
	}
	b, _ := CanonicalJSON(in)
	want := `{"bid":null,"claim_id":"c1","eta":"2026-06-01T10:00:00Z","payload_hash":"` +
		strings.Repeat("0", 64) +
		`","signed_at":"2026-05-23T12:00:00Z","worker_id":"did:wcp:abc"}`
	if string(b) != want {
		t.Fatalf("got %q\nwant %q", string(b), want)
	}
}

func TestSHA256Hex_EmptyVector(t *testing.T) {
	got := SHA256Hex(nil)
	want := "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
	if got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestSHA256Hex_AbcVector(t *testing.T) {
	got := SHA256Hex([]byte("abc"))
	want := "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
	if got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestSHA256Hex_LongVector(t *testing.T) {
	got := SHA256Hex([]byte("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"))
	want := "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
	if got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}
