# WCP Standards-Track Submission Packets

This directory holds the pre-filled submission packets for the three standards bodies WCP targets as part of the v1.0 final and post-v1.0 trajectory:

- **Linux Foundation** (`linux-foundation/`): donate the project to LF Projects LLC; lowest barrier; standard charter conversion.
- **W3C** (`w3c/`): Member Submission for the `did:wcp` method and the protocol as a candidate interaction layer.
- **IETF** (`ietf/`): Internet-Draft for the JSON-RPC-over-WebSocket transport binding, with a path to RFC status if the working group adopts.

The packets are reformattings of the v0.2 spec and governance documents into each body's conventional shape. They are not re-authorings; substantive content is unchanged.

## Recommended sequencing

1. **Linux Foundation first.** Lowest barrier; LF Projects LLC accepts well-governed open-source projects with active community and a written charter. WCP has both. Donation establishes neutral stewardship per `DONATION_COMMITMENT.md`. Estimated 60-120 days from submission to acceptance based on comparable LF onboardings [REASONED].

2. **W3C Member Submission next.** Once LF stewardship is in place, the W3C submission cites LF as the steward and uses the `did:wcp` method spec as the technical anchor. W3C reviews Member Submissions on a published cadence; acceptance to the DID-method registry is a separate, faster path that can run in parallel.

3. **IETF Internet-Draft last.** The IETF path is longest and most uncertain. We submit an individual Internet-Draft via the standard process; if a working group expresses interest (RATS, ACE, or a new working group), the draft migrates to the working group. Without WG adoption, the draft remains an individual contribution and serves as the citable reference for implementers.

The three paths grant different things and require different things. The packets here let the TSC and the post-donation steward execute the sequencing without re-drafting each time.

## What each grants

| Path | Grants |
|---|---|
| LF Projects | Neutral stewardship; trademark management; legal infrastructure; community governance |
| W3C Member Submission | Citation in W3C technical reports; visibility to the DID and verifiable-credentials communities; potential registry entry |
| IETF Internet-Draft | Visibility in the broader transport-protocol community; potential WG adoption; eventual RFC if WG takes up the work |

## What each requires

| Path | Requires |
|---|---|
| LF Projects | Signed charter; named TSC; donation of trademark; community-of-record evidence |
| W3C Member Submission | W3C member organization sponsor; technical document in W3C format; member-submission cover letter |
| IETF Internet-Draft | Individual or working-group author(s); markdown or XML in xml2rfc-compatible form; submission via datatracker.ietf.org |

## What lives in each subdirectory

- `linux-foundation/`: pre-filled LF Projects LLC application packet, proposed LF-format charter, TSC roster template.
- `w3c/`: W3C Member Submission cover letter template, technical contribution document, did:wcp method registration request.
- `ietf/`: Internet-Draft markdown (filename: `draft-wcp-protocol-00.md`), xml2rfc conversion guidance.

## [PRINCIPAL TO PROVIDE] placeholders

Each packet contains explicit `[PRINCIPAL TO PROVIDE: X]` markers where the donating organization (during the pre-donation phase; the steward post-donation) supplies real values:

- LF: signer name and title, donating organization legal entity, initial TSC roster
- W3C: W3C member organization sponsor, contact name, contact email
- IETF: author name(s), author email(s), affiliation

These placeholders are preserved verbatim; the WCP project does not fabricate values for them.
