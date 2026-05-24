# Three-Coordinator Partial-Graph Federation Demo

Companion to the two-coordinator demo at `examples/federation-demo/`.
This variant exercises a partial (non-clique) trust topology to pin
two federation invariants the two-coord demo cannot cover by
construction:

1. **Per-peer descriptor admission** is a property of the
   coordinator's routing layer, NOT the trust anchor. A peer that
   declared `capability_discovery` scope may still be refused for a
   specific descriptor type by the local router's admission policy.
2. **A trust anchor is not a clique.** Three coordinators can run
   with α holding anchors to β and γ while β and γ themselves have
   no relationship. The federation surface continues to work for
   pairs where anchors exist and falls back to local-only behaviour
   for pairs where they don't.

## Topology

```
       coord-alpha
        /        \
       /          \
      /            \
     v              v
 coord-beta    coord-gamma
   (admits        (admits
    transport)    place_on_shelf)
```

`coord-beta` and `coord-gamma` are NOT peered. α's router admits
`transport` only to β, and `place_on_shelf` only to γ.

## Run

```bash
./examples/federation-demo-n3/setup.sh    # clean stale demo databases
./examples/federation-demo-n3/verify.sh   # run the demo
```

`verify.sh` exits 0 on success.

## Pass criteria

`demo.py` exits 0 only when ALL of:

- α records exactly **2** `federation_capability_advertised` entries
  (one for β's worker, one for γ's worker)
- α records exactly **2** `federation_task_forwarded` entries (one
  routed to β, one to γ)
- The forwarded entries name exactly **2 distinct** peer DIDs (the
  router used per-peer descriptor admission, not a single default
  peer for both)
- The integrity scaffold over α's chain remains intact

## What this artifact pins

The two-coord demo proves the federation primitives work; this n3
demo proves the routing layer correctly routes descriptors to
admitted peers and does not assume a complete trust graph. Together
they cover the federation surface the paper's Section 6 claims.
