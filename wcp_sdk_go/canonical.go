package wcp

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
)

// CanonicalJSON produces the canonical JSON encoding used by all WCP SDKs
// for signing and hashing. Sorted keys, no whitespace; matches the Python
// SDK's json.dumps(sort_keys=True, separators=(",", ":")).
func CanonicalJSON(v interface{}) ([]byte, error) {
	switch x := v.(type) {
	case nil:
		return []byte("null"), nil
	case bool, float64, int, int64, string:
		return json.Marshal(x)
	case []interface{}:
		return canonicalArray(x)
	case map[string]interface{}:
		return canonicalObject(x)
	default:
		// Re-encode through json to get the generic form.
		raw, err := json.Marshal(x)
		if err != nil {
			return nil, err
		}
		var generic interface{}
		if err := json.Unmarshal(raw, &generic); err != nil {
			return nil, err
		}
		return CanonicalJSON(generic)
	}
}

func canonicalArray(a []interface{}) ([]byte, error) {
	out := []byte{'['}
	for i, v := range a {
		if i > 0 {
			out = append(out, ',')
		}
		b, err := CanonicalJSON(v)
		if err != nil {
			return nil, err
		}
		out = append(out, b...)
	}
	return append(out, ']'), nil
}

func canonicalObject(m map[string]interface{}) ([]byte, error) {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := []byte{'{'}
	for i, k := range keys {
		if i > 0 {
			out = append(out, ',')
		}
		kj, _ := json.Marshal(k)
		out = append(out, kj...)
		out = append(out, ':')
		vj, err := CanonicalJSON(m[k])
		if err != nil {
			return nil, err
		}
		out = append(out, vj...)
	}
	return append(out, '}'), nil
}

// SHA256Hex returns the lowercase hex SHA-256 of `data`.
func SHA256Hex(data []byte) string {
	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}
