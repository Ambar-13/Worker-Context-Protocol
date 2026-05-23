/**
 * React component: the active job state machine on the contractor side.
 *
 * Drives tasks/execute (heartbeat + events), tasks/attest (final evidence
 * submission), tasks/supervise (escalation) and tasks/abort (cancellation).
 *
 * The state machine mirrors spec/0.1.md Section 1:
 *   claimed -> executing -> attesting -> { settled | disputed | aborted }
 *
 * Per Scenario 5, this component emits a heartbeat every 15 seconds. If
 * the WebSocket is offline at heartbeat time, the heartbeat queues via
 * the service worker bridge and flushes on reconnect.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";

import { AttestationCollector, type AttestationEvidence } from "./attestation-collector";
import { WorkerIdentity, canonicalJsonStringify } from "./identity";
import type { WcpRpcClient } from "./rpc-client";

type LocalState =
  | "opening"
  | "executing"
  | "attesting"
  | "settled"
  | "disputed"
  | "aborted"
  | "supervising"
  | "error";

interface Props {
  identity: WorkerIdentity;
  rpc: WcpRpcClient;
  collector: AttestationCollector;
  claim_id: string;
  onComplete: (state: LocalState) => void;
}

const HEARTBEAT_INTERVAL_MS = 15_000;

export function ExecuteSession({
  identity,
  rpc,
  collector,
  claim_id,
  onComplete,
}: Props): JSX.Element {
  const [state, setState] = useState<LocalState>("opening");
  const [evidence, setEvidence] = useState<AttestationEvidence[]>([]);
  const [verifierDecision, setVerifierDecision] = useState<string | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const sendHeartbeat = useCallback(async (): Promise<void> => {
    const timestamp = new Date().toISOString();
    const payload = { claim_id };
    const sig = await identity.sign({
      claim_id,
      event_type: "heartbeat",
      timestamp,
      payload,
    });
    try {
      await rpc.call("tasks/execute.event", {
        claim_id,
        event_type: "heartbeat",
        timestamp,
        payload,
        sig,
      });
    } catch {
      // queued or ignored; bridge handles offline replay
    }
  }, [identity, rpc, claim_id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await rpc.call("tasks/execute", { claim_id });
        if (!cancelled) setState("executing");
      } catch {
        if (!cancelled) setState("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [rpc, claim_id]);

  useEffect(() => {
    if (state !== "executing") return;
    heartbeatRef.current = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
    return () => {
      if (heartbeatRef.current !== null) clearInterval(heartbeatRef.current);
    };
  }, [state, sendHeartbeat]);

  async function attachEvidence(e: AttestationEvidence): Promise<void> {
    setEvidence((prev) => [...prev, e]);
  }

  async function submitAttestation(): Promise<void> {
    setState("attesting");
    try {
      const res = await rpc.call<{ verifier_decision: string }>(
        "tasks/attest",
        { claim_id, attestations: evidence },
      );
      setVerifierDecision(res.verifier_decision);
      if (res.verifier_decision === "pass") {
        setState("settled");
        onComplete("settled");
      } else {
        setState("error");
      }
    } catch {
      setState("error");
    }
  }

  async function escalate(reason: string): Promise<void> {
    setState("supervising");
    const state_snapshot = { last_event_at: new Date().toISOString() };
    await rpc.call("tasks/supervise", {
      claim_id,
      handoff_reason: reason,
      state_snapshot,
      urgency: "high",
    });
  }

  async function abort(reason: string): Promise<void> {
    const state_snapshot = { last_event_at: new Date().toISOString() };
    await rpc.call("tasks/abort", {
      claim_id,
      reason,
      state_snapshot,
      proposed_settlement: "refund",
    });
    setState("aborted");
    onComplete("aborted");
  }

  return (
    <div className="wcp-execute">
      <div className="wcp-execute-state">State: {state}</div>
      <div className="wcp-execute-evidence">
        <h4>Evidence collected ({evidence.length})</h4>
        <ul>
          {evidence.map((e) => (
            <li key={`${e.mode}:${e.kind}:${e.collected_at}`}>
              {e.mode} / {e.kind}
            </li>
          ))}
        </ul>
      </div>
      <button onClick={submitAttestation} type="button">
        Submit attestation
      </button>
      <button onClick={() => escalate("uncertainty")} type="button">
        Escalate to supervisor
      </button>
      <button onClick={() => abort("worker_initiated")} type="button">
        Cancel job
      </button>
      {verifierDecision && (
        <p className="wcp-verifier">Verifier decision: {verifierDecision}</p>
      )}
    </div>
  );
}
