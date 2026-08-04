# Adopting AAG

Any agent harness that produces JSON conforming to [`../spec/action.schema.json`](../spec/action.schema.json) is an AAG-conformant emitter. This document describes, abstractly, what a harness should do to become one. At the end, as an example, we map [LangChain](https://www.langchain.com/)'s events onto AAG — showing that it is relatively easy to make an existing harness AAG-conformant.

## The model: a harness with hooks

The mechanism an AAG emitter relies on is a pair of hooks around every action — where *action* is broadly any step the harness takes while carrying out a task (a model call, a tool call, an API call, a memory read, and so on). One hook runs just before the action executes, the other just after. Conveniently, this is the structure most agent harnesses — open and closed — already gravitate towards.

In AAG, *each of those steps is an action* — so those two hooks are all you need. The logic is simple:

- **Pre-action hook →** emit the **intended** action (no `output`). This is the
  action *about to* happen — the point at which a security layer can allow or
  deny it, before any effect ([`model.md`](model.md) §2.2).
- **Execute** (unless denied).
- **Post-action hook →** emit the **completed** action: the same `action_id`,
  now with an `output`.

Bracket the run with the task lifecycle, and you have a complete task as described in [`model.md`](model.md) §2.5:

`task.start` → the stream of step actions → `task.end`.

Below we describe the implementation of an AAG-conformant emitter step by step:

## Step 1 — open the task

Emit a `task.start`. Give the run a `task_id`, unique per run — it is the
shared-memory scope ([`model.md`](model.md) §3.1). Carry what you know about the
agent in the `agent` group:

```json
{ "agent_id": "…", "task_id": "run-…", "timestamp": "…", "step_name": "…",
  "type": "task.start", "aag_version": "0.5.0",
  "properties": { "agent": { "risk_classification": "…", "purpose": "…", "environment": "…" } } }
```

## Step 2 — classify each operation

In the pre-action hook, decide the action's **type** and **verb**. The mapping
is mechanical:

| the harness is about to… | type | verb |
|--------------------------|------|------|
| call a model | `step.model` | — |
| call an external tool / API, or read a file | `step.resource` | `GET` to read, `POST`/`PATCH`/`DELETE` to write |
| retrieve from a store (RAG) | `step.resource` | `GET` |
| read or write its own memory | `step.self` | `GET` / `POST` / … |
| read a secret or credential | `step.credential` | `GET` (or a write verb) |
| run code | `step.exec` | — |
| receive from / send to the user (or a parent agent) | `step.message` | `GET` / `POST` |
| run a guardrail, or ask for human approval | `step.gate` | — |
| something it can't classify | `step.unknown` | — |

Set the verb by **data-flow intent, not the transport** ([`model.md`](model.md)
§2.3): Note that a read that carries data outward is a POST.

## Step 3 — emit the intended action

Emit everything you know *except* the result. The absent `output` is what marks
the action **intended**:

```json
{ "agent_id": "…", "task_id": "run-…", "action_id": "act-…", "timestamp": "…",
  "step_name": "get_customer_record", "type": "step.resource", "verb": "GET",
  "input": { "customer_id": "C-4821" },
  "properties": { "target": { "trust": "internal", "host": "crm.internal" },
                  "data": { "classification": "pii" } } }
```

This is the record a security layer can evaluate *before* the agent executes. It is what sets AAG usage apart from standard observability tools.

## Step 4 — emit the finished action

In the post-action hook, emit the completed action: the same `action_id`, now
with the result in `output` (and a `seq`, if you choose to assign one). A failure is still
a completed action — put the error in `output` ([`model.md`](model.md) §2.5):

```json
{ "agent_id": "…", "task_id": "run-…", "action_id": "act-…", "seq": 3, "timestamp": "…",
  "step_name": "get_customer_record", "type": "step.resource", "verb": "GET",
  "input": { "customer_id": "C-4821" },
  "output": { "status": "ok" },
  "properties": { "target": { "trust": "internal", "host": "crm.internal" },
                  "data": { "classification": "pii" } } }
```

## Step 5 — close the task

Emit `task.end` to close the task normally. Use `task.error` if the run terminated abnormally, or `task.idle` if it paused awaiting input — either may be followed by further actions and a later `task.end` (see [`model.md`](model.md) §2.1).

## Properties carry the security meaning

The `type` and `verb` give the baseline; the `properties` are what a security
policy would mostly act upon. Attach what you know at emit time — the trust and host of a
resource (`target.trust`, `target.host`), the sensitivity of the data
(`data.classification`), who is on the other end of a message
(`counterpart.kind`, `counterpart.trust`). None are required; add what your
security rules or policies need ([`model.md`](model.md) §2.4).

## Example: mapping a LangChain harness

Here is how LangChain's callbacks map onto AAG. The pattern is uniform: a
`*_start` callback is the pre-action hook, so it emits the **intended** action;
the matching `*_end` callback is the post-action hook, so it emits the
**completed** one; a `*_error` is a completed action whose `output` records the
failure.

| LangChain event | AAG action | phase |
|-----------------|------------|-------|
| `on_chain_start` (top-level run) | `task.start` | lifecycle |
| run input — the incoming human message | `step.message` `GET` | completed |
| `on_chat_model_start` / `on_llm_start` | `step.model` | intended |
| `on_llm_end` | `step.model` | completed |
| `on_llm_error` | `step.model` | completed (error `output`) |
| `on_agent_action` | `step.resource` (the chosen tool) | intended |
| `on_tool_start` | `step.resource` (+ verb) | intended |
| `on_tool_end` | `step.resource` | completed |
| `on_tool_error` | `step.resource` | completed (error `output`) |
| `on_retriever_start` | `step.resource` `GET` | intended |
| `on_retriever_end` | `step.resource` `GET` | completed |
| `on_retriever_error` | `step.resource` `GET` | completed (error `output`) |
| `on_agent_finish` — the final response to the user | `step.message` `POST` | intended → completed |
| `on_chain_end` (top-level run) | `task.end` | lifecycle |
| `on_chain_error` (top-level run) | `task.error` | lifecycle |
| `on_llm_new_token`, `on_text`, `on_retry`, nested `on_chain_*` | — | no new action |

A few things the mapping, not the callback, decides:

- `on_agent_action` and `on_tool_start` announce the *same* upcoming tool call — emit the intended action once (the former reaches you earliest, the latter carries the concrete arguments).
- LangChain has no dedicated memory or credential callback; a memory read/write or a secret fetch arrives as a tool or retriever call — classify it as `step.self` or `step.credential` if the harness knows what the tool does.
- **the verb** — a tool's declared read/write is a *hint*; classify by what actually crosses the boundary ([`model.md`](model.md) §2.3).
- **the properties** — metadata a tool carries (a `data.classification`, a `target.host`) is forwarded into the action's `properties`, where a policy will look.
