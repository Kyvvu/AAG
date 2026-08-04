# The AAG model

This document describes the details of the Agent Action Grammar (AAG): We describe in detail what an *action* is, what assumptions we make about agents for the AAG to be meaningful, and we detail the exact meaning attached to each action type. Note that the machine-readable form lives in [`../spec/vocabulary.yaml`](../spec/vocabulary.yaml). This document is aimed at human readers and aims to explain the AAG in detail.

## 1. Introduction

It is useful to keep the purpose of the AAG in mind when reading. The AAG is a unified vocabulary for the actions an agent carries out, so that **agent-security systems (or humans) can reason over and control** a fleet of diverse agents — each running a different harness — through one shared description, instead of building a separate integration for every framework and vendor. Please note that **agent security is the aim the AAG is shaped by**; the same uniform record can also feed observability and governance systems, but those are downstream consumers, not the design goal. 

> Note that we assume agent *harness*(es) to emit the actions specified by the AAG, not the LLM(s) that drives the harness. Clearly, it would be beneficial if the action plan emitted by an LLM also simply emitted AAG-structured actions. However, for the sake of agent security we deem the LLM(s) to be untrusted sources of data in this context (the LLM emits a plan, it does not note what actually happened). The harness, the software that actually executes the actions, should be the prime source of AAG actions.

The general structure the AAG describes for handling an agent carrying out a task is conceptually simple: an agent starts a task (and emits a `task.start` action), next, the agent carries out multiple steps (`step.xxx` actions) which each have a meaningful `type`, `verb`, and `properties`, and keeps submitting steps until the task ends. A few intricacies are however good to keep in mind when reading:

1. The AAG provides semantics for what the agent does. The `type` and `verb` carry the baseline meaning of an action; the `properties` are where an emitter, building an agent for a specific purpose, adds the semantics that elaborate security policies and rules are written against.
2. The AAG is explicitly designed to reason in a security-relevant way over *tasks*: a task is the unit within which the agent's memory — and therefore the data available to it — is assumed to accumulate. This memory model (§3.1) is what makes the task the right boundary, and it drives how sub-agents and multi-agent systems are handled (see §3.4).
3. The AAG is intentionally designed to adapt to the currently quite common convention in agent harnesses to implement hooks that allow for checking conditions *prior to* and *after* executing the action. The AAG facilitates this use by the simple idea that each `step.xxx` action is conceptually composed of a triplet: {metadata, arguments, result} — which in a record are the `properties`, `input`, and `output` fields. When the result (`output`) is void, we interpret this as the "intended" action. Needless to say, this has its obvious uses in security applications when restricting what an agent does before the damage has been done.

Thus, the AAG describes a uniform way of describing what an agent is doing — what actions it is taking — *as it is carrying out a task*. The AAG explicitly does not cover any methods of *securing* based on this description; security policies and rules can be built once the AAG is adopted, and for now we leave that to others. We are solely concerned with having a unified, meaningful (for agent security) *description* of what an agent does as it is pursuing its task.

One point of vocabulary, since it recurs throughout: we use **action** as the general term for any record a harness emits — both the `task.*` lifecycle markers and the `step.*` behaviors are thus "actions" in our writing here. However, we use **step** specifically for a `step.*` action. A `task.start` is therefore an action but not a step, and the triplet of point 3 above applies to steps, not to task markers.

### The structure of this document

- **§2 Specification:** The normative core of the AAG. The anatomy of an action and its fields; the action `type`s; the `verb`s; and the `properties`. This section mirrors the machine-readable [`vocabulary.yaml`](../spec/vocabulary.yaml). The tables in this section are simply the human-readable form of the `.yaml` file. The `vocabulary.yaml` file is the versioned, machine-readable source of truth and takes priority over anything detailed in §2. This section, however, adds meanings and examples beyond the machine-readable specification.
- **§3 Implications**: A detailed account of how the specification is meant to be *read* for agent security: the task as a memory scope, trust boundaries, paths, and the handling of sub-agents. Nothing new is standardized here; this section simply provides the emergent meaning that is provided by tying the tables in §2 together.
- Points that are **not** yet settled — open design questions and the alternatives under consideration — are kept out of this document; they live in the accompanying [RFC(s)](../rfc/README.md), so the specification here stays focused on what *is* decided.

---

## 2. Specification

### 2.1 Action types

The AAG consists of twelve action types: four `task.*` lifecycle types and eight `step.*` types which describe agent behavior within a task. Any `(type, verb)` pair not listed in the tables below is malformed and not a part of the AAG.

#### Task lifecycle (`task.*`, no verb)

| type         | meaning & security implication                                                                                  |
|--------------|----------------------------------------------------------------------------------------------------------------|
| `task.start` | Opens a task. Establishes a fresh memory scope — nothing is carried from prior tasks. May carry agent, task, or organizational context (§2.4): e.g. the agent's risk tier, purpose, and environment. |
| `task.end`   | Closes a task. The task's memory scope ends; nothing *implicitly* survives into another task.                                |
| `task.error` | The task terminated abnormally. Marks an incomplete path — may indicate a blocked or failed step. The task may resume after an error.               |
| `task.idle`  | The task is paused (e.g. awaiting input). Memory is assumed to persist across the idle period — the agent is still on the same task. There is no explicit resume marker: the next action on the task signals resumption (the same holds after `task.error`).    |

#### Steps (`step.*`)

| type              | verbs                    | meaning                                                                                                    |
|-------------------|--------------------------|-----------------------------------------------------------------------------------------------------------|
| `step.resource`   | GET, POST, PATCH, DELETE | The general workhorse: a call to a resource or tool. GET reads; POST/PATCH/DELETE write. Most "tool calls" (MCP calls, internal tools, file reads, etc.) will be a `step.resource` step coupled with a verb and semantic properties (see below).|
| `step.message`    | GET, POST                | Communication with whatever the agent is interacting with — a human user, a parent agent (§3.4), or the trigger that started an automatically-invoked agent. GET receives, POST sends. The counterpart's security posture varies (a logged-in human differs from a parent agent), so trust is not assumed — see §3.2 and §3.4. |
| `step.self`       | GET, POST, PATCH, DELETE | The agent acting *on its own state (e.g. memory)*. Writes may alter state that persists across tasks (§3.3). It's these steps that make changes to the agent state explicit instead of implicit. |
| `step.model`      | —                        | A model invocation. Both sends context to the model and receives a completion, so no single verb applies. Data is both exfiltrated and infiltrated. |
| `step.credential` | GET, POST, PATCH, DELETE                      | A read or write of sensitive material (a secret or credential): GET retrieves a secret; the write verbs create, modify, or remove one. A read or write of a `.env` file would be a prime example.                                     |
| `step.exec`       | —                        | Code execution. May be internally or externally scoped through the properties, but warrants its own type.                                                  |
| `step.gate`       | —                        | A gate — a guardrail (a check of contents / data that serves as input or output of preceding or following steps) or human approval. Its **decision (pass/deny) is the action's `output`**; `input` is what was checked. A distinct type since agent-paths often require a gate to precede a sensitive step (e.g. human approval before an outbound POST). |
| `step.unknown`    | —                        | Catch-all: the agent did something that could not be classified. Usually a thing to prevent, but useful to capture improper harnesses whose event emission is incomplete.            |

#### One tool call, one action

Some harnesses reach many tools through a single connection — an MCP server, for example, exposes multiple tools at one endpoint. The emitter maps each *tool invocation* to its own action, with its own `verb` and `properties` — not one action per server or per connection. The specific tool goes into the `properties` (see below) so one can tell calls within one server apart. Any read/write hint the tool interface advertises is only input to classifying the action and hence gives the action its `verb`. A tool billed as a read that carries task data outward takes a write verb in the AAG. (thus implying `HTTP GET != AAG GET`).

### 2.2 Anatomy of an action

As stated, an agent carries out a task (`task.start`), runs through multiple actions (i.e., `step.message` to get user input, `step.model` to generate a response, etc.) until task completion (`task.end`).

Every *individual* action a harness emits has three conceptual layers:

- **Positioning** — where the action sits in the stream, so records from different harnesses can be grouped and ordered: `agent_id`, `task_id`, `seq`, `timestamp`, and the human-readable label `step_name`.
- **Classification** — *what kind* of action it is: its `type` (§2.1), and — for `step.x` types that take one — a `verb` (§2.3).
- **Content** — the aforementioned triplet {metadata, arguments, result} = {`properties`, `input`, `output`}. For a `step.x`, an absent `output` is interpreted to signal an **intended** action (pre-execution). When `output` is present the action is deemed **completed**. 

The following fields are explicitly part of the AAG:

| layer          | field               | required | meaning                                                                                   |
|----------------|---------------------|----------|-------------------------------------------------------------------------------------------|
| positioning    | `agent_id`          | ✅       | Stable identifier of the agent performing *this action*. A single task may contain actions from more than one agent when they share memory (§3.4). |
| positioning    | `task_id`           | ✅       | The logical task — one shared-memory scope. Unique per run; groups every action of the task, the unit reasoned over (§3.1). A task may span several agents that share memory (§3.4). |
| positioning    | `parent_task_id`    | ❌       | On `task.start` only: the `task_id` of the task that spawned this one (§3.4).              |
| positioning    | `action_id`         | ❌       | Identifier of one action. Emitted on an intended record and repeated on the record that settles it — completed or denied — so the two can be tied together. (How denials are recorded is an open question — see the [RFC](../rfc/0001-agent-action-vocabulary.md).) |
| positioning    | `seq`               | ❌       | Sequence number within the task. Absent for an intended action; assigned when recorded.    |
| positioning    | `timestamp`         | ✅       | When the harness emitted the action.                                                       |
| positioning    | `step_name`         | ✅       | Human-readable label (`"post_invoice"`, `"chat_gpt-4o"`).                                  |
| classification | `type`              | ✅       | The action type — one of the twelve in §2.1.                                               |
| classification | `verb`              | ⚠️※     | `GET` / `POST` / `PATCH` / `DELETE`. See §2.3. ※ Required only for step types that take a verb; absent for all others. |
| classification | `aag_version`       | ❌       | On `task.start` only: the AAG version the stream conforms to. (Out-of-band version negotiation is discussed in the [RFC](../rfc/0001-agent-action-vocabulary.md).) |
| content        | `properties`        | ❌       | Nested contextual object — the metadata that gives the action its security meaning (§2.4).  |
| content        | `input`             | ❌       | The arguments to the action.                                                              |
| content        | `output`            | ❌       | The result of the action. Absent ⇒ *intended* (steps only).                                |

Please note that **task and step actions are not symmetric.** 

* A `task.*` action — a lifecycle marker such as `task.start` — carries positioning, a `type`, and *context* properties (§2.4). It has no `verb`, and neither the `input` (arguments) nor `output` (result) of the triplet: only its metadata (`properties`) is present. Also, most `agent.` properties (see below) will be part of a `task.*` action, not an individual `step.*`.
* A `step.*` action carries the full triplet. The intended/completed distinction therefore applies to **steps only**: a `task.start` with no `output` is not an "intended" action, it is a lifecycle marker.

### 2.3 Verbs

A `verb` records the **data-flow intent** of a step, not the literal HTTP method a tool happened to use. The question a verb answers is: does task data **leave**, or does external data **enter**? And, if data leaves, what does it do to the external resource / target?

| verb     | meaning                                                                 |
|----------|-------------------------------------------------------------------------|
| `GET`    | Data enters the task; nothing task-resident meaningfully leaves.          |
| `POST`   | Task data leaves the task, or state outside the task's memory is created.  |
| `PATCH`  | State outside the task's memory is modified.                              |
| `DELETE` | State outside the task's memory is removed. Destructive actions.          |

"Outside the task's memory" is deliberately wider than "external": a `step.self` write crosses no external boundary, but it does write state that outlives the task (§3.3), and it takes a write verb for exactly that reason.

Verbs are **qualifiers scoped to a type**: each type declares which verbs are legal for it (the *verbs* column in §2.1). Some types take no verb at all — including `step.model`, where data flows both ways (context out, completion in) and a single direction would be misleading.

The four verbs answer two different questions, and those working with the AAG can use them on two axes:

- **Data flow (the path axis).** Here the only distinction that matters is *in* vs. *out*: `GET` versus the three write verbs. An "outbound" rule matches `POST`, `PATCH`, **and** `DELETE` alike — not `POST` alone.
- **Operational effect (the harm axis).** Among the write verbs, *what the write does to the state it touches* differs — create, modify, destroy. This is why three write verbs are kept rather than one: it lets a policy forbid a class of effect outright (e.g. an agent that may never emit `DELETE`), independently of any data-flow reasoning.

Both axes are useful for understanding the actual behavior of an agent.

### 2.4 Properties

Beyond `type` and `verb`, an action can carry a nested `properties` object: a tree of named groups holding contextual details. At its core, **no property is required, and the set is open.** An emitter may add any group or leaf it needs, and a consumer must tolerate ones it does not recognize.

What the AAG provides is a set of *suggested* namespaces with agreed meanings, so that the properties that matter for agent security are named the same way everywhere rather than reinvented per harness. A group is only worth naming when it carries information the action `type` does **not** already imply. So the suggested groups are the cross-cutting ones — `target` (which resource), `auth` (under whose authority), `data` (what kind of data), `agent` (information about the agent itself), and `counterpart` (who is on the other end of a `step.message`) — plus `transport` and `raw` as freeform envelopes. `transport` holds the mechanics of a call (protocol, latency, status codes); `raw` holds the emitter's untranslated native record; the AAG defines no leaves inside either. As the standard matures — assuming the twelve action types stay stable — this is where more will be pinned down; today only a handful of properties carry defined leaves.

#### Suggested properties

Based on our current use of the AAG, we *suggest* the following properties:


| property                    | example values                                              | meaning                                                                 |
|-----------------------------|-------------------------------------------------------------|-------------------------------------------------------------------------|
| `target.host`               | `api.billing.com`, `crm.internal`                           | The concrete resource endpoint an action reaches.                        |
| `target.trust`              | `external`, `internal`                                      | Whether that resource sits inside or outside the trust boundary (§3.2).  |
| `auth.principal`            | `svc-invoices`, `user:j.vij`                                | The identity under whose authority the action runs.                      |
| `auth.method`               | `oauth2`, `api_key`, `delegated`                            | How that authority was obtained.                                         |
| `counterpart.kind`          | `user`, `parent_agent`, `trigger`                           | Who is on the other end of a `step.message` (§3.4).                      |
| `counterpart.trust`         | `trusted`, `untrusted`                                      | The trust granted to that counterpart (§3.2, §3.4).                      |
| `kind`                      | `human`, `guardrail`                                        | Whether a `step.gate` was human approval or an automated check. A bare leaf, scoped by the type. (The gate's pass/deny *decision* is the action's `output`, not a property.) |
| `data.classification`       | `pii`, `secret` (open vocabulary)                           | Sensitivity of the data the action handles.                              |
| `agent.risk_classification` | `high`, `limited`, `minimal`, `unacceptable`, `unclassified`| EU AI Act risk tier the agent runs under.                                |
| `agent.purpose`             | free text                                                   | What the agent is for.                                                   |
| `agent.environment`         | `development`, `staging`, `production`                      | The deployment environment.                                             |
| `agent.version`             | free text (e.g. a semver or commit)                         | Which revision of the agent ran — its prompt, config, or code version.   |
| `command`                   | `git push`, `rm -rf /`                                      | The command a `step.exec` ran. A bare leaf — the `step.exec` type already scopes it. |
| `provider`                  | `openai`, `anthropic`                                       | The model provider, for a `step.model`. A bare leaf (maps to OTel `gen_ai.system`). |
| `model`                     | `gpt-4o`, `claude-sonnet-4-6`                               | The model identifier, for a `step.model`. A bare leaf (maps to OTel `gen_ai.request.model`). |

A few notes:

* The `agent.*` properties describe the *agent*, not an individual step, so they are carried once on `task.start` rather than repeated on every action.
* `data.classification` is deliberately an **open** vocabulary: organizations have their own labels, and a fixed sensitivity set would be wrong for almost everyone. The same holds for the property tree as a whole — the AAG names what recurs, and leaves the rest open.
* There are two distinct `kind` leaves: the bare `kind` on a `step.gate` (`human` / `guardrail`) and `counterpart.kind` on a `step.message` (`user` / `parent_agent` / `trigger`). They never collide — one is bare (scoped by `step.gate`), the other is grouped — but they are different vocabularies; do not unify them.

All other properties are effectively open.

### 2.5 Putting it all together

Each action is assumed to be emitted as a single JSON object. A task is simply a stream of these objects that share one `task_id`, ordered by `seq`. Nothing else ties them together — a consumer reconstructs the task by grouping on `task_id` (which is assumed unique).

Here is one completed step — a support agent reading a customer record:

```json
{
  "agent_id": "support-assistant",
  "task_id": "run-7b3d90",
  "action_id": "act-51c2",
  "seq": 5,
  "timestamp": "2026-07-30T09:14:22Z",
  "step_name": "get_customer_record",
  "type": "step.resource",
  "verb": "GET",
  "input": { "customer_id": "C-4821" },
  "output": { "status": "ok", "record": { "name": "Jordan Vij", "email": "j.vij@example.com" } },
  "properties": {
    "target": { "trust": "internal", "host": "crm.internal.example.com" },
    "data":   { "classification": "pii" }
  }
}
```

Reading it against the three layers of §2.2:

- **Positioning** — `agent_id`, `task_id`, `seq`, `timestamp`, `step_name`: this is action 5 of task `run-7b3d90`, run by `support-assistant`.
- **Classification** — `type` + `verb`: a `step.resource` GET, i.e. a read from a resource outside the agent. No sensitive data leaves the agent at this step.
- **Content** — the triplet `input` / `output` / `properties`: the arguments, the result, and the semantic metadata. Here the metadata says the read reached an *internal* host and pulled *pii* into the task — the two facts an upstream security policy would key on.

The same action, submitted *before* execution by a pre-execution hook, simply omits `output` (and typically has no `seq` yet). Its `action_id` is what ties it to the record that later settles it — completed, or denied. (See the [RFC](../rfc/0001-agent-action-vocabulary.md) for how denials are recorded.) This is the **this-action-is-intended** form:

```json
{
  "agent_id": "support-assistant",
  "task_id": "run-7b3d90",
  "action_id": "act-51c2",
  "timestamp": "2026-07-30T09:14:22Z",
  "step_name": "get_customer_record",
  "type": "step.resource",
  "verb": "GET",
  "input": { "customer_id": "C-4821" },
  "properties": {
    "target": { "trust": "internal", "host": "crm.internal.example.com" },
    "data":   { "classification": "pii" }
  }
}
```

A note on failure. **(1) A step that fails to execute** — the tool threw, a request timed out — is still a *completed* step: its `output` records the failure (e.g. `{"status": "error"}`). There is no step-level error type; the triplet already expresses it. **(2) `task.error`** is a lifecycle marker for the *task* reaching an abnormal state — an unrecoverable harness fault, or a halt — not tied to any one step; the task may resume afterwards, so a log can contain a `task.error` followed by further steps. **(3) An action blocked by a rule or policy** is a third case, and one the AAG does not itself represent — the AAG describes behaviour, it does not enforce. When an engine blocks an *intended* action (a `step.x` that never gains an `output`), the block may surface as a `task.error` if it halts the task, or as the intended action re-emitted with a denial `output`. Exactly how a block is recorded is left to the [RFC](../rfc/0001-agent-action-vocabulary.md) (see *Recording blocked actions*).

Below is an example of a full (short) task for illustration purposes. It runs from `task.start` to `task.end` — the stream a harness emits for one run. A realistic task interleaves model calls (to plan, then to compose the answer) with the resource and message steps. Note that `task.*` actions carry no `verb` and no `input`/`output`; `task.start` carries agent context in the `agent` group; and each `step.model` output is itself a source (§3.1). The model `input`/`output` here are shown only in outline — the AAG does not require their content (see §3.1; input/output granularity is discussed in the [RFC](../rfc/0001-agent-action-vocabulary.md)):

```json
[
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 0,
    "timestamp": "2026-07-30T09:14:20Z",
    "step_name": "handle_support_ticket_4821",
    "type": "task.start",
    "aag_version": "0.5.0",
    "properties": {
      "agent": {
        "risk_classification": "high",
        "purpose": "answer customer billing questions",
        "environment": "production",
        "version": "2.3.1"
      }
    }
  },
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 1,
    "timestamp": "2026-07-30T09:14:21Z",
    "step_name": "receive_user_question",
    "type": "step.message",
    "verb": "GET",
    "output": { "text": "Why was I charged twice?" }
  },
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 2,
    "timestamp": "2026-07-30T09:14:22Z",
    "step_name": "plan_next_step",
    "type": "step.model",
    "input": { "messages": "[system prompt + user question]" },
    "output": { "text": "Look up the billing record for customer C-4821." },
    "properties": { "provider": "openai", "model": "gpt-4o" }
  },
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 3,
    "timestamp": "2026-07-30T09:14:23Z",
    "step_name": "get_customer_record",
    "type": "step.resource",
    "verb": "GET",
    "input": { "customer_id": "C-4821" },
    "output": { "status": "ok" },
    "properties": {
      "target": { "trust": "internal", "host": "crm.internal.example.com" },
      "data":   { "classification": "pii" }
    }
  },
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 4,
    "timestamp": "2026-07-30T09:14:24Z",
    "step_name": "compose_reply",
    "type": "step.model",
    "input": { "messages": "[system prompt + question + retrieved record]" },
    "output": { "text": "You were charged once; the second line is a pending authorization." },
    "properties": { "provider": "openai", "model": "gpt-4o" }
  },
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 5,
    "timestamp": "2026-07-30T09:14:25Z",
    "step_name": "reply_to_user",
    "type": "step.message",
    "verb": "POST",
    "input": { "text": "You were charged once; the second line is a pending authorization that will drop off." },
    "output": { "status": "sent" }
  },
  {
    "agent_id": "support-assistant",
    "task_id": "run-9f2ac1",
    "seq": 6,
    "timestamp": "2026-07-30T09:14:26Z",
    "step_name": "ticket_resolved",
    "type": "task.end"
  }
]
```

Read as a *path* (§3.1): the model calls (`seq` 2 and 4) and the record read (`seq` 3) all bring data *into* the task — they are sources — and the reply (`seq` 5) sends data *out*, a sink. Because that sink is `step.message` back to the human user who asked, this is likely a legitimate reply, not exfiltration. The same `pii` read followed by a `step.resource POST` to an `external` host would be the shape an upstream security or governance system might flag.

A fuller version of this task — with an exfiltration-review `step.gate` before the reply, and realistic prompts — is shipped as [`examples/tasks/support_ticket.ndjson`](../examples/tasks/support_ticket.ndjson).

---

## 3. Implications

The tables in §2 already carry the meaning of each type, verb, and property. This section explains the reasoning behind them — why the vocabulary is shaped this way, and how it is meant to be read for agent security. This section adds nothing to the grammar itself; it adds to the meaning we humans give the grammar.

### 3.1 The task as a memory scope

The AAG makes one core assumption about how an agent's memory behaves:

> **Within one `task_id`, any data that has entered the agent's memory via *any* action is assumed to remain available to *every* later action in that same task. A new `task_id` starts fresh — nothing carries over *implicitly*.**

In other words, memory (and therefore *taint* — the influence of sensitive or externally-controlled data) is **monotonic and task-scoped**:

- **Monotonic:** once financial data is read at step 3, steps 4…N are all assumed to *potentially* carry it. The AAG never assumes an agent "forgot" something mid-task.
- **Task-scoped:** `task.start` opens a fresh scope; `task.end` closes it. Two different `task_id`s share nothing implicitly; anything carried between them must appear as an explicit action (see §3.3).

Under this assumption the object to reason about is the *path* — the ordered sequence of actions from the start of the task till the end of the task as opposed to simply reasoning about individual steps. Why? Because a `GET` from an external API and a later *write* (a `POST`, `PATCH`, or `DELETE`) to a different one are each, as individual steps, likely unremarkable. However, the same two in sequence, in one task, form a data exfiltration path. The formal argument for reasoning about paths is in *Runtime Governance for AI Agents: Policies on Paths*, Kaptein, Khan & Podstavnychy (2026), but the short version is simply that the order of steps matters for security and governance, the order is decided at runtime by the agent, and hence the whole path needs to be accounted for.

It helps to read each action as either bringing data *into* the task or sending data *out* of it — loosely, a **source** or a **sink**. A source followed by a sink within one task is the shape a path policy looks for. The AAG only records the actions and their properties; deciding what to do about a given sequence is left to whatever consumes the stream. Please note that a (LLM) model call is a source and a sink itself. Because the LLM is — from the perspective of the AAG — untrusted (§1), the completion returned by a `step.model` is external data entering the task — it taints exactly as an external read does.

**Classification reflects the deed, not the words.** An action's `type`, `verb`, and `properties` describe *what the agent did* — a read from an external host, a write of `pii` — as known to the harness that executed it. They are never derived from the text of an LLM prompt or completion. The `input` and `output` fields may record that content for audit, but the content has no bearing on how an action is classified, and a consumer should not need to read it to know what happened. This is deliberate: it keeps the description robust and stops the untrusted model's own words from deciding how its behavior is labelled.

### 3.2 Trust boundaries

A simple security-related rule like "no write to an external boundary after an internal read" is only expressible if an action records *which side* of a trust boundary it touched. The AAG carries such semantics easily: the `type` already says a lot (a `step.message` is the user channel, a `step.credential` reaches a secret store), and for `step.resource` actions the suggested `target` properties — `target.trust` (`external` / `internal`) and `target.host` (the concrete endpoint) — refine it. Such rules can then be expressed straightforwardly on top of an AAG-emitting agent.

The distinction that matters most in many practical cases is **user vs. external**. Prompt-injection is exactly the case where content from an external source is treated as though it came from a user. Because the AAG puts the user channel in its own type (`step.message`) and untrusted fetches in another (`step.resource` with `target.trust: external`) such situations are easy to tell apart.

### 3.3 `step.self` and durable memory

The clean-slate rule of §3.1 does not say that an agent's own state must be wiped at `task.end`. It says something narrower: nothing enters a task *implicitly*. Durable memory — a scratchpad or a vector store the agent owns that outlives the task — is fully compatible with the model, because access to it is mediated by observable actions:

- Memory is **read** into a later task via `step.self GET` — a source, classifiable like any other read.
- Memory is **written** via `step.self POST` — a sink into a store that outlives the task.

So cross-task influence is not assumed away; it becomes *visible* as a `step.self GET` in the later task. The path stays complete. A `step.self` write within the task is internal — it crosses no external boundary — but the deployment should recognize that such a write is what makes data outlive the task: an agent that uses durable memory may warrant a gate before `step.self POST`, since that write is the moment task data is persisted beyond the task.

### 3.4 Sub-agents and multi-agent tasks

A task is precisely a **shared-memory scope** (§3.1), and that one idea settles how sub-agents and multi-agent systems are represented:

- **Shared memory → one task.** When an agent spawns sub-agents that share working memory to complete a single goal, they are, in AAG terms, the *same task*: they emit under one `task_id`. The `agent_id` then varies from action to action, recording which agent acted, while the task stays the memory (and taint) scope. Nothing special is required — the path is simply the interleaved stream of all their actions.
- **Separate memory → separate tasks.** When an agent hands work to another agent that has its own memory, that is a *new task* — a fresh blank slate (§3.1). The hand-over is not implicit: it is a `step.message POST` from the first agent that enters the second as a `step.message GET`. The two tasks are linked by `parent_task_id` (§2.2) on the child's `task.start`, and — because the parent is not a trusted human — the receiving `step.message` should carry `counterpart.kind: parent_agent` with an explicit `counterpart.trust` (§2.4), so the child does not mistake the brief for a trusted user instruction.

**Ordering.** Within one (possibly multi-agent) task, `seq` *is* the order, assigned where actions are logged — typically the parent or coordinating agent, incrementing `seq` as each action is recorded. If the order of actions matters for security it must be serialized; running actions concurrently under one `task_id` deliberately relaxes the order. `timestamp` stays advisory (wall-clock, subject to skew).

This is the AAG's *suggested* handling — really just a way of using the existing grammar, with no new machinery. Whether it is the right or only approach — and whether the `counterpart` trust marking should be *required* on a hand-over — is left open for the [RFC](../rfc/0001-agent-action-vocabulary.md).

