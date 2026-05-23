# did:wcp Method Specification v0.1

**Status:** draft
**Conforms to:** W3C DID Core 1.0 (Recommendation, 2022-07-19)

This document registers the `did:wcp` DID method used by the Worker Context Protocol for worker, principal, and agent identity.

---

## 1. Method name

`wcp`

A DID using this method has the syntax:

```
wcp-did      = "did:wcp:" wcp-identifier
wcp-identifier = base58(public-key-bytes)         ; Ed25519 by default
              | base58(pubkey-bytes) ":" path     ; for hierarchical issuers
```

Examples:

```
did:wcp:8FCQz2bN7y4kQvKZqxPm3hRsT5wYjHbA6dL9XfMnEqRk
did:wcp:8FCQz2bN7y4kQvKZqxPm3hRsT5wYjHbA6dL9XfMnEqRk:agent-pool-1
```

---

## 2. Method-specific identifier

The identifier is the base58-encoded public key of the controlling Ed25519 keypair. Implementations MAY use other curves declared in the DID document `verificationMethod` array; the identifier remains bound to the initial key for backward compatibility with reputation lookups.

Curve choice rationale: Ed25519 is the default for performance (mobile and embedded), small key size (32 bytes), and ubiquity in modern crypto libraries [verified].

---

## 3. DID document

A minimal `did:wcp` document:

```json
{
  "@context": ["https://www.w3.org/ns/did/v1"],
  "id": "did:wcp:8FCQz2bN7y4kQvKZqxPm3hRsT5wYjHbA6dL9XfMnEqRk",
  "verificationMethod": [{
    "id": "did:wcp:8FCQz2bN7y4kQvKZqxPm3hRsT5wYjHbA6dL9XfMnEqRk#key-1",
    "type": "Ed25519VerificationKey2020",
    "controller": "did:wcp:8FCQz2bN7y4kQvKZqxPm3hRsT5wYjHbA6dL9XfMnEqRk",
    "publicKeyMultibase": "z..."
  }],
  "authentication": ["#key-1"],
  "assertionMethod": ["#key-1"],
  "service": [{
    "id": "#wcp-coordinator",
    "type": "WcpCoordinator",
    "serviceEndpoint": "wss://coordinator.rentably.ai/wcp"
  }],
  "wcp:metadata": {
    "schema_version": "wcp/0.1",
    "registered_at": "2026-05-23T00:00:00Z",
    "class_hint": "human | autonomous_robot | teleoperated_robot | semi_autonomous | hybrid"
  }
}
```

The `wcp:metadata.class_hint` is informative only. The canonical worker class is on the CapabilityDescriptor.

---

## 4. CRUD operations

### 4.1 Create

A new `did:wcp` is created by generating an Ed25519 keypair and computing the identifier as `base58(pubkey)`. No on-chain registration is required at v0.1; identity is bound by signature.

Implementations MAY publish DID documents to a coordinator-maintained registry. Publication is OPTIONAL; resolution falls back to inline DID document fetch from a `serviceEndpoint`.

### 4.2 Read (resolve)

Resolution proceeds:

1. Parse the identifier.
2. Query the coordinator-maintained registry at `https://<coordinator>/.well-known/did-wcp/<identifier>`.
3. If absent, attempt to fetch a DID document from any URI registered in a prior CapabilityDescriptor.
4. Validate the DID document signature using the public key encoded in the identifier.

### 4.3 Update

The DID document MAY be updated by signing a new version with the current authentication key. Key rotation appends a new `verificationMethod` and marks the old one as `revoked: true` with a `revoked_at` timestamp.

### 4.4 Deactivate

A DID is deactivated by publishing a DID document with `deactivated: true`. Deactivated DIDs MUST NOT be assigned new claims by coordinators. Their reputation history remains queryable.

---

## 5. Security considerations

- **Key compromise.** A worker who suspects key compromise SHOULD immediately rotate via update and publish the revocation. Outstanding tasks claimed under the compromised key remain bound to the worker DID, but new claims require the new key.
- **Identifier reuse.** The base58-of-pubkey identifier prevents an attacker from claiming a chosen DID without generating the matching keypair.
- **Cross-class portability.** A single worker DID may be used across human and robot work modes. Coordinators MUST NOT segment reputation by class internally; the unified worker DID is the canonical reputation root.

---

## 6. Privacy considerations

- DIDs are not personal identifiers in the PDPA sense by themselves. Coordinators MAY link a DID to a verified human identity (KYC) under their own privacy policy.
- The DID document MAY contain a `service` entry pointing to the coordinator. This exposes the worker's primary coordinator publicly. Workers who require coordinator privacy SHOULD use a relay endpoint.

---

## 7. Method-specific extensions

Future RFCs MAY register additional `wcp:*` extension keys in the DID document. v0.1 reserves:

- `wcp:metadata` (mandatory if any wcp:* extension is present)
- `wcp:reputation_pointer` (URI to a coordinator-maintained reputation record)
- `wcp:supervisor_pool` (DID of the human supervisor pool, for semi-autonomous workers)

End of did-method-wcp.md
