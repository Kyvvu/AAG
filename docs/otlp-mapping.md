# Mapping AAG to OpenTelemetry (OTLP)

> **AAG is for security; OTLP is for observability.** Two things AAG carries that an OTLP trace does not:
>
> 1. the **intended action** — an action described *before* it executes, so a security layer can allow or deny it. An OTLP span is, by construction, a record of something that already happened.
> 2. a **closed vocabulary** — AAG's action types and verbs are a fixed set; OTLP span names are an open surface, so once projected the vocabulary is advisory, not enforced.
>
> This mapping is therefore one-directional and lossy on purpose. Use the AAG to secure a task *as it runs*; then — once the task is done and you hold the whole thing — it is natural to log and observe it. That is what this document is for: handing a finished task to your observability stack.

## The shape

A **task** becomes a **trace**; each **action** becomes a **span** under a single task-root span.

- The `task_id` derives the `trace_id` — via any stable function (e.g. a hash of `task_id`) — so a task's spans share one trace across flushes.
- The task gets one root span (kind `INTERNAL`); every action is a child span of it.
- A `parent_task_id` (a spawned sub-task, see [`model.md`](model.md) §3.4) becomes a span **link** to the parent task's trace.

**On timing.** AAG actions are point-in-time records, usually emitted after the fact; each carries a `timestamp`, not a duration. The spans here are therefore effectively zero-duration markers — the value is in the **attributes and the parent/child structure**, not in span timing. Do not read latency from these spans.

## Field mapping

| AAG | OTLP | notes |
|-----|------|-------|
| a task (actions sharing `task_id`) | one **trace** | |
| `task_id` | `trace_id` (derived) + `aag.task_id` | stable derivation so a task's spans share a trace |
| an action | one **span**, child of the task root | |
| `type` | span **name** + `aag.type` | e.g. `step.model`; append `step_name` for readability |
| `verb` | `aag.verb` | absent for verbless types |
| `seq` | span order + `aag.seq` | |
| `timestamp` | span **start** (and end — zero duration) | |
| `agent_id` | `aag.agent_id` | |
| `step_name` | `aag.step_name` | |
| `action_id` | `aag.action_id` | ties an intended action to its completion, if both are logged |
| `parent_task_id` | span **link** to the parent trace | sub-agent / multi-agent |
| `properties.<group>.<leaf>` | `aag.<group>.<leaf>` (flattened) | e.g. `aag.target.trust`, `aag.data.classification` |
| a bare leaf (`command`, `kind`) | `aag.<leaf>` | |
| `input` / `output` | `aag.input` / `aag.output`, or a span **event** | optional; may be summarized or omitted (privacy — see the RFC) |

**Reusing OTel semantic conventions.** Where a property has a natural OTel equivalent you *may* also emit the standard attribute, for tools that speak plain OTel — for example `target.host` → `server.address`, or a `step.model`'s provider and name → `gen_ai.system` / `gen_ai.request.model`. 

## The intended action does not map

An intended action — a step with no `output` ([`model.md`](model.md) §2.2) — is the moment a security layer decides to allow or deny, *before* execution. A span cannot represent it faithfully, because a span records what happened. So:

- **The OTLP projection is the completed-action view.** Emit spans for completed actions; the intended action lives only in the AAG stream your security layer consumed.
- If you want the *decision* visible downstream, carry it on the completed action's span as a policy result (below) — not as a separate "intended span."

## Where policy and rule results go

AAG is the vocabulary that **security policies and rules are written against** (see the [README](../README.md)); it does not define those policies, nor their results. But when your security layer evaluates an action, that verdict is exactly what an observability log should carry — and the natural place is **on the action's own span**, beside the `aag.*` attributes:

| what | suggested attribute |
|------|---------------------|
| the decision for this action | `aag.policy.decision` — `allow` / `warn` / `block` |
| rules evaluated | `aag.policy.rules` |
| rules that fired | `aag.policy.violations` |
| a violation's severity | `aag.policy.severity` |

Each span then tells the whole story: *what the agent did* (the AAG fields) and *what the security layer decided about it* (the policy result(s)), in one place, ready to index. The result format is your engine's concern; AAG only supplies the action it was evaluated against.

## Example

A completed `step.resource` GET:

```json
{ "agent_id": "support-assistant", "task_id": "run-9f2ac1", "seq": 3,
  "timestamp": "2026-07-30T09:14:23Z", "step_name": "get_customer_record",
  "type": "step.resource", "verb": "GET",
  "properties": { "target": { "trust": "internal", "host": "crm.internal" },
                  "data": { "classification": "pii" } } }
```

becomes a child span:

```
name:        step.resource
start/end:   2026-07-30T09:14:23Z   (zero duration)
attributes:
  aag.task_id             = run-9f2ac1
  aag.agent_id            = support-assistant
  aag.seq                 = 3
  aag.type                = step.resource
  aag.verb                = GET
  aag.step_name           = get_customer_record
  aag.target.trust        = internal
  aag.target.host         = crm.internal
  aag.data.classification = pii
  aag.policy.decision     = allow          # from the security layer, if any
  server.address          = crm.internal   # optional OTel-semconv courtesy
```
