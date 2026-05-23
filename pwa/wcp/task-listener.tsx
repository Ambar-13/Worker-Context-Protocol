/**
 * React component: lists eligible WCP tasks via capabilities/subscribe
 * stream and exposes the claim flow to the contractor.
 *
 * INTEGRATION-GAP: in a worker-provider's existing contractor application this
 * component mounts into the existing job list page; styling and shell come
 * from the parent app.
 */

import React, { useEffect, useState } from "react";

import { WorkerIdentity, canonicalJsonStringify } from "./identity";
import type { WcpRpcClient } from "./rpc-client";

export interface TaskSummary {
  task_id: string;
  posted_by: string;
  descriptor_type: string;
  amount: string;
  eta_required_by: string;
  location_label: string;
}

interface Props {
  identity: WorkerIdentity;
  rpc: WcpRpcClient;
  onClaimed: (claim_id: string, task_id: string) => void;
}

export function TaskListener({ identity, rpc, onClaimed }: Props): JSX.Element {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [claiming, setClaiming] = useState<string | null>(null);

  useEffect(() => {
    const off = rpc.onStreamEvent((event) => {
      if (event.event_type !== "task_posted") return;
      const payload = event.payload as Partial<TaskSummary>;
      if (!payload || !payload.task_id) return;
      setTasks((prev) => [payload as TaskSummary, ...prev]);
    });
    return () => {
      off();
    };
  }, [rpc]);

  async function claim(task: TaskSummary): Promise<void> {
    setClaiming(task.task_id);
    try {
      const eta = task.eta_required_by;
      const bid = null;
      const payload_hash = await WorkerIdentity.sha256Hex(
        new TextEncoder().encode(canonicalJsonStringify({ task_id: task.task_id })),
      );
      const signed_at = new Date().toISOString();
      const acceptance = {
        sig: await identity.sign({
          task_id: task.task_id,
          worker_id: identity.did,
          eta,
          bid,
          payload_hash,
          signed_at,
        }),
        alg: "Ed25519",
        payload_hash,
        signed_at,
      };
      const res = await rpc.call<{ claim_id: string; accepted: boolean }>(
        "tasks/claim",
        {
          task_id: task.task_id,
          worker_id: identity.did,
          eta,
          acceptance_attestation: acceptance,
        },
      );
      if (res.accepted) onClaimed(res.claim_id, task.task_id);
    } finally {
      setClaiming(null);
    }
  }

  return (
    <div className="wcp-task-list">
      {tasks.length === 0 && (
        <p className="wcp-empty">No tasks available right now.</p>
      )}
      <ul>
        {tasks.map((t) => (
          <li key={t.task_id} className="wcp-task">
            <div className="wcp-task-type">{t.descriptor_type}</div>
            <div className="wcp-task-location">{t.location_label}</div>
            <div className="wcp-task-amount">SGD {t.amount}</div>
            <button
              disabled={claiming === t.task_id}
              onClick={() => claim(t)}
              type="button"
            >
              {claiming === t.task_id ? "Claiming..." : "Claim"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
