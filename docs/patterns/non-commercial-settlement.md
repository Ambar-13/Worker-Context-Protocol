# Pattern: Non-Commercial Settlement

How to use WCP in deployments where the value flow is NOT a monetary payment between parties: scientific research, disaster response, public infrastructure, regulatory monitoring, internal-corporate operations, and similar contexts where settlement is about accounting, attribution, or compliance rather than commerce.

## Why this exists

WCP's settlement primitive is intentionally generic: it records a value flow with an `escrow_provider`, a `currency`, an `amount`, and a `split[]`. The primitive is shaped like commercial payment because commercial payment is one common case, but the same primitive serves many non-monetary purposes:

- **Internal cost allocation:** a robotics-lab deployment where the "settlement" is a budget transfer between departments.
- **Grant attribution:** a research deployment where work is paid by a grant; settlement records which grant funded which task.
- **Volunteer effort logging:** a disaster-response deployment where workers are volunteers and "settlement" is the audit record of their contribution.
- **Regulatory cost recovery:** a public-monitoring deployment where the audit chain feeds into a regulator's cost-recovery calculation.
- **Carbon accounting:** a deployment where each task records a carbon-equivalent measurement instead of a monetary amount.

None of these cases need real money to move. All of them benefit from a recorded, signed, tamper-evident statement of *what was done, by whom, for what attribution*.

## The pattern

Use the standard settlement primitive with a non-commercial escrow provider that:

- Does not move money (no API calls to a payment processor, no balance updates)
- Does record the settlement event in the audit chain with full provenance
- May produce a non-monetary side-effect: a budget journal entry, a grant report row, a volunteer-hours log entry, a carbon-accounting row
- Returns settlement success on a defined condition (typically: the attested task is well-formed)

### `escrow_provider` choices

Operators in this pattern configure one of:

| Provider name (convention) | Behavior |
|---|---|
| `internal-cost-allocation` | Logs a journal entry to the deployment's accounting system; no money moves |
| `grant-attribution` | Tags the task with a grant ID; periodically rolls up into grant reporting |
| `volunteer-hours` | Records worker-hours into a volunteer log keyed by DID |
| `carbon-accounting` | Treats `amount` as kg-CO2-equivalent; rolls up into the deployment's carbon report |
| `no-settlement` | No external side-effect at all; the audit chain entry is the only record |

These are operator conventions, not registered names. The protocol does not enforce semantics; the coordinator's `escrow_provider` config points at whichever Python/Rust/Go/TS class implements the provider interface.

## Currency field in non-commercial mode

The `currency` field still appears in the descriptor, but in non-commercial mode it labels the unit of account:

```
"settlement": {
    "currency": "HOURS",           # volunteer-hours mode
    "amount": "0.5",
    "escrow_provider": "volunteer-hours",
    "split": [{"party": "did:wcp:volunteer-7", "pct": 100}]
}
```

```
"settlement": {
    "currency": "KGCO2EQ",          # carbon accounting
    "amount": "1.2",
    "escrow_provider": "carbon-accounting",
    "split": [{"party": "did:wcp:carbon-ledger", "pct": 100}]
}
```

Operators using non-ISO currency labels SHOULD pick a label distinct from ISO 4217 codes so consumers of the audit chain cannot confuse the two. Use uppercase prefixes (`HOURS`, `KGCO2EQ`, `GRANT-NSF-1234567`) rather than codes that look like real currencies.

## Domain examples

### Scientific research

A lab runs a remote-instrument scheduling deployment. Researchers post tasks for instrument time; instruments are workers; the deployment is internal to one institution.

- `escrow_provider = "internal-cost-allocation"`
- `currency = "INSTRUMENT_HOURS"`
- `amount` = the hours of instrument time consumed
- `split[]` allocates the cost to the requesting researcher's grant code, parsed from the agent's DID metadata

The audit chain serves as the lab's source of truth for instrument utilization. The lab's annual report aggregates audit chain entries by grant code.

### Disaster response

A disaster-response coalition runs a deployment where worker organizations (NGOs, municipal teams, volunteer brigades) accept tasks posted by a central incident command.

- `escrow_provider = "no-settlement"` OR `"volunteer-hours"`
- `currency = "HOURS"` if logged; otherwise omitted
- `amount` = the volunteer-hours
- `split[]` = the contributing organization's DID

When the response concludes, the audit chain is exported to the relevant emergency management agency as the official contribution record. No money flows; the record is the deliverable.

### Public-infrastructure monitoring

A municipality monitors stormwater infrastructure with a sensor fleet plus periodic ground inspectors. Settlement is internal cost allocation; the audit chain feeds a federally-required compliance report.

- `escrow_provider = "internal-cost-allocation"`
- `currency = "USD"` (real cost basis, but the money flow is intra-municipal accounting, not a payment)
- `amount` = the standard cost rate * hours
- `split[]` = the municipal department's accounting code

### Carbon accounting overlay

Any deployment may add carbon accounting as a *parallel* settlement track: each task settles in its primary currency (USD or whatever) AND records a KGCO2EQ side-settlement.

This is done with two `settle` calls on the same claim:

```
{"settle_primary": {"currency": "USD", "amount": "8.50", "escrow_provider": "stripe"}}
{"settle_secondary": {"currency": "KGCO2EQ", "amount": "0.45", "escrow_provider": "carbon-accounting"}}
```

The protocol's settlement extension fields are operator-defined; the coordinator records both audit chain entries with explicit semantics.

## Override authority in non-commercial mode

The override authority concept is still useful in non-commercial deployments:

- For grant-funded work: the grant administrator's DID
- For volunteer work: the coalition's safety officer DID
- For internal cost allocation: the department head's DID
- For carbon accounting: the deployment's sustainability officer DID

The override authority's role is the same as in commercial mode: adjudicate disputes about whether the work was performed and whether the recorded settlement was correct.

## What still has to be real

Even in non-commercial mode, the audit chain has the same security properties: hash-linked, tamper-evident, signed at each step. The forensic record is real; only the value-transfer side-effect is metaphorical.

This means non-commercial deployments are NOT lower-stakes from an audit perspective. The audit chain in a carbon-accounting deployment is exactly as security-critical as the audit chain in a commercial payment deployment, and operator-side audit-chain durability/backup matters the same.

## Compliance posture in non-commercial deployments

| Concern | Note |
|---|---|
| Tax | Operators MUST consult tax counsel; "no money moved" is not always tax-neutral (in-kind contributions and volunteer hours have tax implications in some jurisdictions) |
| Data residency | The audit chain still contains DIDs and task metadata; non-commercial mode does not exempt the deployment from GDPR/CCPA/etc. |
| Regulatory reporting | If the deployment feeds a compliance report, the audit chain's signatures and timestamps must satisfy the regulator's evidentiary standards |
| Charity / non-profit governance | Charity deployments using `volunteer-hours` mode MUST consult their governance body about whether the recorded values become part of the organization's accounting records |

## See also

- `docs/limits/wcp-is-not.md` for what WCP does NOT provide on the settlement side (no money holding, no compliance substitute)
- `rfcs/0010-rpc-tasks-settle.md` for the settlement RPC semantics
- `rfcs/0032-cross-coordinator-settlement-clearing.md` for cross-coordinator settlement (commercial-oriented but applicable to non-commercial too)
