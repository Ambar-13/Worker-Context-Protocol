package wcp

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"fmt"

	"golang.org/x/crypto/curve25519"
)

// base58 alphabet (Bitcoin-style). Used for did:wcp identifiers.
const b58Alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

func base58Encode(b []byte) string {
	// Convert bytes to big.Int via repeated division.
	var n uint64
	digits := make([]byte, 0, 64)
	src := append([]byte(nil), b...)
	leading := 0
	for _, x := range src {
		if x == 0 {
			leading++
		} else {
			break
		}
	}
	for {
		isZero := true
		var rem int
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
	// Avoid unused import warnings on platforms where curve25519 is referenced.
	_ = curve25519.PointSize
	_ = n
}

// Identity carries an Ed25519 keypair and the did:wcp identifier.
type Identity struct {
	priv ed25519.PrivateKey
	pub  ed25519.PublicKey
	DID  string
}

func newIdentity() (*Identity, error) {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, fmt.Errorf("ed25519 keygen: %w", err)
	}
	return &Identity{
		priv: priv,
		pub:  pub,
		DID:  "did:wcp:" + base58Encode(pub),
	}, nil
}

// PublicKeyB64URL returns the URL-safe base64 (no padding) of the 32-byte pubkey.
func (i *Identity) PublicKeyB64URL() string {
	return base64.RawURLEncoding.EncodeToString(i.pub)
}

// Sign produces an ed25519 signature over canonical-JSON(payload).
func (i *Identity) Sign(payload interface{}) (string, error) {
	bytes, err := CanonicalJSON(payload)
	if err != nil {
		return "", err
	}
	sig := ed25519.Sign(i.priv, bytes)
	return "ed25519:" + base64.RawURLEncoding.EncodeToString(sig), nil
}

// NewWorkerIdentity returns a fresh worker identity.
func NewWorkerIdentity() (*Identity, error) { return newIdentity() }

// NewAgentIdentity returns a fresh agent identity.
func NewAgentIdentity() (*Identity, error) { return newIdentity() }
