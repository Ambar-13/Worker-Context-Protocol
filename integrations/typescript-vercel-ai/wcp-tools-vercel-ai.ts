/**
 * WCP tools for the Vercel AI SDK.
 *
 * Worked-example domains: logistics, disaster-response.
 *
 * The Vercel AI SDK's `tool` helper accepts a Zod schema. This module exports
 * `makeWcpTools(agent)` returning four tools matching the Anthropic / OpenAI /
 * Gemini / LangChain set: discover, post, subscribe, audit.
 *
 * Depends on `@vercel/ai` and `zod`, plus the WCP TS SDK at `wcp_sdk_typescript/`.
 */

import { z } from "zod";

// The Vercel AI SDK's tool() helper has moved across versions; we import via
// a lazy require to keep this module importable without the optional dep.
type ToolHelper = (def: unknown) => unknown;

export interface WcpAgentBinding {
  did: string;
  discoverCapabilities(filter: Record<string, unknown>): Promise<unknown>;
  postTask(task: Record<string, unknown>, args: { }): Promise<unknown>;
}

export function makeWcpTools(agent: WcpAgentBinding, tool: ToolHelper): Record<string, unknown> {
  const PostInput = z.object({
    descriptor_type: z.string(),
    descriptor_payload: z.record(z.any()),
    attestation_modes: z.array(z.string()),
    M: z.number().int().default(1),
    N: z.number().int().default(1),
    amount: z.string(),
    currency: z.string(),
    worker_class_filter: z.array(z.string()).default(["human"]),
    time_window_hours: z.number().default(4),
  });

  return {
    wcp_discover_capabilities: tool({
      description: "Discover WCP workers eligible for a task.",
      parameters: z.object({
        worker_class_filter: z.array(z.string()).optional(),
        location_scope: z.record(z.any()).optional(),
      }),
      execute: async (args: Record<string, unknown>) =>
        agent.discoverCapabilities(args),
    }),
    wcp_post_task: tool({
      description: "Post a WCP task descriptor with bonded escrow.",
      parameters: PostInput,
      execute: async (args: z.infer<typeof PostInput>) => {
        const now = new Date();
        const task = {
          schema_version: "wcp/0.2",
          task_id: crypto.randomUUID(),
          posted_by: agent.did,
          descriptor_type: args.descriptor_type,
          descriptor_payload: args.descriptor_payload,
          constraints: {
            time_window: {
              earliest: now.toISOString(),
              latest: new Date(now.getTime() + args.time_window_hours * 3600 * 1000).toISOString(),
            },
            worker_class_filter: { allowed: args.worker_class_filter },
          },
          attestation_requirement: {
            modes: args.attestation_modes,
            threshold: "M-of-N",
            M: args.M,
            N: args.N,
            evidence_schema: args.attestation_modes.map((m) => ({ mode: m, kinds: [] })),
            override_authority: "did:wcp:example-operator-ops",
            override_audit_required: true,
          },
          settlement: {
            currency: args.currency,
            amount: args.amount,
            escrow_provider: "example-escrow",
            split: [{ party: "did:wcp:worker-pool", pct: 100 }],
          },
          supervision: { default: "autonomous" },
          "x-subcontract-allowed": false,
        };
        return agent.postTask(task, {
          }`,
          expiry: new Date(now.getTime() + 24 * 3600 * 1000).toISOString(),
        });
      },
    }),
    wcp_subscribe_attestation: tool({
      description: "Subscribe to attestation outcomes for a posted task_id.",
      parameters: z.object({ task_id: z.string() }),
      execute: async ({ task_id }: { task_id: string }) => ({ subscribed: true, task_id }),
    }),
    wcp_get_audit_chain: tool({
      description: "Fetch the audit chain for a task_id.",
      parameters: z.object({ task_id: z.string() }),
      execute: async ({ task_id }: { task_id: string }) => ({
        task_id,
        note: "audit-chain endpoint pending",
      }),
    }),
  };
}
