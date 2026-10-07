# Mapping AAG to the OWASP Agent Control Standard (ACS)

> Here we try to map and compare OWASP's [ACS](https://github.com/GenAI-Security-Project/agent-control-standard) to the Agent Action Grammar as presented in this repo. Note that ACS is still in its early stages; we write this against ACS spec v0.1.0 (repository release 0.1.3, commit `770f1e0`), read on 2026-10-06. Issue and Discussion numbers (`#n`) refer to the ACS repository on that date. We hope the write-up helps shape these distinct efforts into, ultimately, a single accepted standard by which harnesses emit what they are doing and can be governed uniformly.

## Summary

ACS and AAG are two different, but complementary, efforts to standardize reasoning about agent behavior. Both focus on monitoring agent behavior at the level of the agent harness (which should emit its actions). ACS defines the full loop between the harness and a distinct "Guardian": a process that returns a decision on each step. AAG is narrower: it describes solely the behavior of the agent (the steps an agent takes while going about a task). AAG classifies each step more finely than ACS does: a closed set of action types and verbs, and one record shape for a step before and after it runs. ACS carries things AAG does not, among them data lineage per argument and an authenticated approval flow. We propose changes to both ACS and AAG to bring the two closer together.

## Some context...

AI agents decide what to do next at run time, by asking a model. Since agents act directly (a harness carries out the instructions an LLM provides), they are both very powerful and a source of new security risks. AAG was created from a simple idea: for many security questions that matter, the problem is rarely a single action. It is the *order* in which individually-permitted actions are combined. Hence, we need to reason about the "path" an agent is taking. Reasoning about the path across a fleet of differently-built agents needs a shared way to name what an agent is doing. This is what the **Agent Action Grammar (AAG)** in this repo is: a standardized description of the steps an agent takes, specified in a security-meaningful way.

> The argument for treating the path, rather than the isolated action, as the thing to control is in *[Runtime Governance for AI Agents: Policies on Paths](https://arxiv.org/abs/2603.16586)* (Kaptein, Khan & Podstavnychy, 2026).

The **Agent Control Standard (ACS)**, from the OWASP GenAI Security Project, has a larger focus than AAG. It standardises the hook a harness sends before each action and the decision a "Guardian" returns. ACS does not prescribe the policy engine or the policies the Guardian implements. It does specify what a Guardian must do alongside those policies: log every decision, keep a hash-chained record of the session, and follow fixed rules when a harness cannot honour a decision.

In our view, compared to AAG, ACS adds, among other things:

* The transmission protocol (JSON-RPC over http(s) or stdio).
* A standardized "envelope" (version, id, metadata) around each step.
* A result (the decision of the Guardian).
* Session state on the Guardian side: an ordered, hash-chained record of the session, and optional data provenance.

AAG asks only "how do we describe an agent's behavior, as it goes about its task, in a security-meaningful way?". ACS asks "how do we set up the interaction between a harness and a Guardian, so that any harness can be governed in a uniform way?". Describing behavior is a part of ACS, but a small part.

This document positions AAG inside ACS and tries to identify implications, both ways, that in our view would improve both. Ideally, if you ask us, AAG would be included in ACS as the detailed description of what an agent is doing inside the control loop.

To bring AAG and ACS closer together, we are taking a number of proposals to the ACS repository. [Section 6](#6-discussions-to-extend-acs) describes them; in short:

* The ACS "hook name" and the AAG "type" answer the same question. We propose that ACS hooks cover every AAG type (proposal 1).
* ACS records the read / write / delete distinction on *some* hooks and not others. We propose it does so on tool calls as well (proposal 2).
* AAG's open `properties` have no slot in ACS today. We propose one (proposal 3).

ACS additionally defines the Guardian's answer. On most of it AAG has no opinion. There is one "sticky" point on which the two specifications differ: ACS treats human approval as a Guardian decision (`ask`), while AAG treats any approval as a step on the agent's path (proposal 4, and [section 5.3](#53-approval-a-decision-in-acs-a-step-in-aag)). When designing AAG we consciously kept actions inside the harness, not inside a policy engine or Guardian.

### References

- ACS repository: <https://github.com/GenAI-Security-Project/agent-control-standard> (read at commit `770f1e0`)
- ACS site: <https://agentcontrolstandard.org/>
- AAG: <https://github.com/Kyvvu/AAG> · the model in [`model.md`](model.md) · the vocabulary in [`../spec/vocabulary.yaml`](../spec/vocabulary.yaml)
- *Policies on Paths*: <https://arxiv.org/abs/2603.16586>

## 1. The shared backdrop

Underneath AAG and ACS sits one simple idea: just before an agent takes a step, the harness makes what it is *about to do* explicit, so it can be checked before it happens rather than audited after.

In this context, AAG simply names each step an agent takes: what kind of action, which way data flows, what it touches. That's it. ACS takes the same pre-step moment and builds the whole control loop around it: the step travels as a hook, a Guardian evaluates it against the session so far and returns a decision, and the harness honours that decision. [Section 2](#2-what-acs-does) describes this loop. [Section 3](#3-where-aag-fits) returns to the one piece AAG and ACS both describe, the step itself.

## 2. What ACS does

This section describes ACS in more detail. In the rare cases where the ACS schemas and the ACS prose seem to disagree, we follow the schemas ([section 8](#8-where-the-acs-schemas-and-prose-differ) lists the cases we ran into).

### Parties

- The **Observed Agent** is the harness. It emits hooks and applies the decisions it gets back.
- The **Guardian** evaluates each hook against its policies and returns a decision. It must log every decision.
- An **Approver** (a human, an agent or a service) is consulted when the Guardian's decision is `ask`.

### Hooks

A hook is a JSON-RPC request from the Observed Agent to the Guardian. It carries a method name, which says what kind of step this is, and a payload that depends on the method:

```json
{
  "jsonrpc": "2.0",
  "method": "steps/toolCallRequest",
  "id": 23,
  "params": {
    "acs_version": "0.1.0",
    "request_id": "…",
    "timestamp": "…",
    "metadata": { "agent_id": "…", "session_id": "…" },
    "payload": { },
    "signature": { }
  }
}
```

ACS defines 19 hooks under `steps/`:

| Group | Hooks |
|---|---|
| Session and turn | `sessionStart`, `sessionEnd`, `agentTrigger`, `turnStart`, `turnEnd` |
| Messages | `userMessage`, `agentResponse` |
| Knowledge and memory | `knowledgeRetrieval`, `memoryContextRetrieval`, `memoryStore` |
| Tools | `toolCallRequest`, `toolCallResult` |
| Compaction | `preCompact`, `postCompact` |
| Subagents | `subagentStart`, `subagentStop` |
| Skills | `skillRegister`, `skillLoad`, `skillUnload` |

Three points about these hooks return in later sections:

- **Not every hook is required.** A conformant harness must emit `sessionStart`, `userMessage` or `agentTrigger`, `toolCallRequest`, `toolCallResult`, `agentResponse` and `sessionEnd` (and `subagentStart` if it spawns subagents). The other hooks are recommended. At the start of a session, in the handshake, the harness declares which hooks it will emit (`methods_implemented`).
- **Most actions arrive as `toolCallRequest`.** ACS requires this hook for "every action that escapes the agent's reasoning context": file reads and writes, network calls, shell commands.
- **MCP traffic has its own namespace.** A session that uses MCP wraps it under `protocols/MCP/`. An MCP tool call may arrive as `toolCallRequest` or as `protocols/MCP/tools/call`.

### What a tool call carries

The payload of `toolCallRequest` has these fields:

| Field | Required | Meaning |
|---|---|---|
| `tool.name` | yes | the tool being called |
| `arguments` | yes | the arguments, each as `{ "value": … }` |
| `capability` | no | a free string naming what the call does, e.g. `filesystem.delete`, `network.egress`, `process.execute`. We found no enumerated list of values |
| `operation` | no | a free string: the tool's own sub-operation, when a tool offers several |
| `raw_command` | no | the command string, for tools that take one |

`memoryStore` has a field with the same name, `operation`, that is a closed list: `create`, `update` or `delete`.

### Decisions

The Guardian answers each hook with one of five decisions (ACS calls them dispositions):

| Decision | Meaning |
|---|---|
| `allow` | proceed |
| `deny` | do not proceed |
| `modify` | proceed with changes the Guardian supplies |
| `ask` | pause; an Approver decides |
| `defer` | pause; the Guardian has not reached a verdict yet |

### Session record and provenance

The Guardian keeps an ordered record of each session and chains its entries by hash, so that later tampering can be detected.

Optionally (the ACS-Provenance profile), every piece of content on a hook carries its origin (`user_input`, `tool_output`, `retrieved`, …) and the items it was derived from (`derived_from`). A Guardian can then follow data from one step to the next. ACS leaves judging whether an origin is trusted to the Guardian's policy; it is not sent on the hook.

ACS also defines an inventory of the agent's components (the AgBOM), a mapping of hooks to OpenTelemetry and OCSF, and conformance profiles. We do not rely on these below.

## 3. Where AAG fits

Of everything in section 2, AAG speaks to one thing: the step a hook is about. AAG is a vocabulary for that step. (The full vocabulary is in [`model.md`](model.md).)

An AAG event can be derived from an ACS hook: a consumer maps the method name and the payload to an AAG `type`, `verb` and `properties`. [Section 5](#5-the-mapping) gives that mapping. Compared with an ACS hook, an AAG event has three things:

1. **A closed classification.** Every step is one `(type, verb)` pair from a fixed, versioned table. There are twelve types (four `task.*` types that mark the lifecycle of a task, and eight `step.*` types, such as `step.resource`, `step.message`, `step.model` and `step.exec`) and four verbs (`GET`, `POST`, `PATCH`, `DELETE`). A verb says which way data flows, not which HTTP method was used.
2. **One record for before and after.** A step without an `output` is the intended step, on which a decision is taken. The same step with an `output` is the completed step. ACS has a second hook for the result only for tool calls (`toolCallResult`).
3. **Named properties.** These are the facts a rule keys on, such as whether the target is inside or outside a trust boundary (`target.trust`) or how sensitive the data is (`data.classification`). The set is open; AAG suggests names for the common ones.

AAG stops there. It defines no decision, no session state and no transport. A policy engine consumes AAG events and decides (we are developing one at Kyvvu); that engine is out of scope here.

### 3.1 ACS classifies a step in two places

AAG puts the whole classification in `(type, verb)`. ACS spreads it over two places.

**The hook name.** It separates messages, memory, knowledge retrieval and tool calls. For the first three, the hook name already gives the AAG type (`step.message`, `step.self`, `step.resource`).

**The `capability` string, on tool calls only.** For a tool call the hook name says only "tool call". What kind of tool call it is sits in the optional `capability` string. That string combines several things. With ACS's own examples:

| ACS `capability` | Domain | Action | In AAG |
|---|---|---|---|
| `filesystem.delete` | filesystem | delete | type `step.resource`, verb `DELETE`; the domain is a property of the target |
| `datastore.read` | datastore | read | type `step.resource`, verb `GET`; the domain is a property of the target |
| `network.egress` | network | data leaves | type `step.resource`, a write verb; `target.trust: external` |
| `process.execute` | process | execute | type `step.exec` |

So one ACS string holds three things that AAG keeps apart: a type (`process.execute` is `step.exec`), a verb (`read`, `delete`, `egress`) and a property (the domain).

Our first three proposals ([section 6](#6-discussions-to-extend-acs)) separate them: the type goes into the hook name, the verb into a closed field, and the target into a `resource` field, with an open object for further properties. It is useful to note what this does to `capability`: with the above three fields in place, a `capability` string on an individual call says nothing the other fields do not already say. `capability` would keep the role those fields cannot fill, which is to declare in advance what a tool or a skill may do, before any call is made. A Guardian then checks what a call does against what was declared.

## 4. A task, end to end

Here we provide a running example of both ACS and AAG based on a simple "support agent" answering a billing question. The agent reads an internal customer record containing personal data, calls a model, and then tries to send data to an external host before replying.

| # | What happens | ACS hook | AAG event |
|---|---|---|---|
| 0 | task opens | `sessionStart` | `task.start` |
| 1 | user asks a question | `userMessage` | `step.message` `GET` |
| 2 | read the customer record | `toolCallRequest`, then `toolCallResult`; `capability: "datastore.read"` | `step.resource` `GET`; `target.trust: internal`, `data.classification: pii` |
| 3 | call the model to draft a reply | none | `step.model` |
| 4 | send data to an external host | `toolCallRequest`; `capability: "network.egress"` | `step.resource` `POST`; `target.trust: external` |
| 5 | reply to the user | `agentResponse` | `step.message` `POST` |
| 6 | task closes | `sessionEnd` | `task.end` |

A few observations:

* **Row 3.** ACS has no hook for a model call; [#122] proposes one. AAG records the call as `step.model`: context leaves for the model provider, and the completion that comes back is untrusted data.
* **Row 4.** An outbound `POST` (row 4) after an internal read of personal data (row 2) is the shape of an exfiltration. 

An ACS Guardian can catch the exfiltration in two ways:

- *By lineage.* Under the optional ACS-Provenance profile, the harness tags each argument of the outbound call with `derived_from` links back to the customer record, and a rule follows the data. This asks the harness to track value-level lineage, which is a real cost.
- *By path.* Without provenance, the Guardian has seen `datastore.read` and then `network.egress`, and has to know by itself that the first read was internal and contained personal data.

Catching the exfiltration using AAG is more straightforward: AAG puts the two facts directly in the events, so that a rule over the order of events can use them (and one could easily write a generic rule that prevents exfiltration after *any* internal data read).

We see these as complementary. Lineage follows data where it can be tracked. The order of steps still applies where it cannot, for instance once data has passed through the model.

Row 2 in full, first as the ACS hook and then as the AAG event derived from it:

```json
{
  "jsonrpc": "2.0",
  "method": "steps/toolCallRequest",
  "id": 23,
  "params": {
    "acs_version": "0.1.0",
    "request_id": "0b1f6e9c-4d1a-4c57-9d3e-2f6a8b7c1e55",
    "timestamp": "2026-07-30T09:14:23Z",
    "metadata": {
      "agent_id": "support-assistant",
      "session_id": "5a0c2d6e-91b4-4e0f-8a67-3c9f2ac1d0b7"
    },
    "payload": {
      "tool": { "name": "crm.lookup" },
      "capability": "datastore.read",
      "arguments": { "customer_id": { "value": "C-4821" } }
    },
    "signature": { "algorithm": "HMAC-SHA256", "value": "…", "key_id": "…" }
  }
}
```

```json
{
  "agent_id": "support-assistant",
  "task_id": "5a0c2d6e-91b4-4e0f-8a67-3c9f2ac1d0b7",
  "action_id": "act-23",
  "timestamp": "2026-07-30T09:14:23Z",
  "step_name": "crm.lookup",
  "type": "step.resource",
  "verb": "GET",
  "input": { "customer_id": "C-4821" },
  "properties": {
    "target": { "trust": "internal", "host": "crm.internal.example.com" },
    "data":   { "classification": "pii" }
  }
}
```

The hook says that a datastore is read. The AAG event adds that the datastore is internal and that the data is personal. In ACS those two facts seem to be left to the Guardian's policy.

## 5. The mapping

The table lists every ACS hook and every AAG type. An empty cell means the other side has no counterpart.

| ACS | AAG | Note |
|---|---|---|
| `sessionStart` | `task.start` | |
| `subagentStart` | same task (shared memory), or `task.start` with `parent_task_id` (own memory) | (AAG) a subagent that shares memory is flattened into one task, varying only `agent_id`; one with its own memory is a new task linked by `parent_task_id` (`model.md` §3.4). (ACS) a subagent always opens its own session |
| `sessionEnd`, `subagentStop` | `task.end` or `task.error` | (AAG) `task.error` when the ACS `reason` / `outcome` is an error or a timeout |
| | `task.idle` | (AAG) no ACS counterpart |
| `userMessage` | `step.message` `GET` | |
| `agentTrigger` | `task.start` context, or `step.message` `GET` if the trigger is a message | (ACS) a trigger may be a user message, a schedule, or a system event; (AAG) only a message-bearing trigger is a `step.message` — a scheduled or system start is just `task.start` |
| `agentResponse` | `step.message` `POST` | (ACS) fires before delivery, so the intended step |
| `memoryContextRetrieval` | `step.self` `GET` | (ACS) fires after the read, so the completed step |
| `memoryStore` | `step.self` `POST` / `PATCH` / `DELETE` | (AAG) the verb follows the ACS `operation` (`create` / `update` / `delete`) |
| `knowledgeRetrieval` | `step.resource` `GET` | (ACS) fires after the retrieval, so the completed step |
| `toolCallRequest`, `toolCallResult` | `step.resource` + verb | (ACS) the verb is not on the hook (proposal 2) |
| `protocols/MCP/tools/call`, `protocols/MCP/resources/read` | `step.resource` + verb | |
| `toolCallRequest` with `capability: process.execute` | `step.exec` | (ACS) identified only by an optional `capability` string (proposal 1) |
| `toolCallRequest` | `step.credential` | (ACS) no capability name for it (proposal 1) |
| | `step.model` | (ACS) no hook (proposal 1) |
| the `ask` decision (not a hook) | `step.gate` | [section 5.3](#53-approval-a-decision-in-acs-a-step-in-aag), proposal 4 |
| `toolCallRequest` without `capability` | `step.unknown` | |
| `turnStart`, `turnEnd` | | [section 5.4](#54-acs-hooks-without-an-aag-type) |
| `preCompact`, `postCompact` | | [section 5.4](#54-acs-hooks-without-an-aag-type) |
| `skillRegister`, `skillLoad`, `skillUnload` | `step.self` or `step.resource` (no dedicated type) | (AAG) could be `step.self` (the agent changing its own capabilities) or `step.resource` (fetching a definition); a dedicated type is optional ([section 5.4](#54-acs-hooks-without-an-aag-type)) |

### 5.1 Verbs

An AAG verb says which way data flows and what happens to the state it touches. ACS has the same distinction in a few places: `memoryStore.operation`, the separate hooks for reading memory and knowledge, and words inside `capability` strings such as `datastore.read`. On a tool call it has no fixed field for it. Proposal 2 asks for one, with these values:

| AAG verb | Meaning | Proposed ACS value |
|---|---|---|
| `GET` | data enters the task; nothing meaningful leaves | `read` |
| `POST` | task data leaves, or state outside the task is created | `create` |
| `PATCH` | state outside the task is modified | `update` |
| `DELETE` | state outside the task is removed | `delete` |

`step.exec`, `step.model` and `step.gate` take no verb.

### 5.2 Why a type per class of action

ACS sends code execution, access to secrets, file operations and network calls through the same hook, `toolCallRequest`, and tells them apart by the optional `capability` string. AAG gives each class its own type. We think the type should be fixed, for three reasons:

- **A rule should hold on every harness.** "Code execution needs an approval first" is one rule. If the class is a free string, each harness can spell it differently or leave it out, and the rule has to be rewritten per harness.
- **A missing label is ambiguous.** When `capability` is absent, a Guardian cannot tell "no code was executed" from "this harness does not label code execution". A hook name does not have this problem: the harness declares its hooks at the start of the session, so the Guardian knows what it can expect to see.
- **Each class has controls of its own.** Code execution calls for sandboxing and an allowed-command list. Access to a secret calls for rules on who may read which secret. A model call sends the context to a provider and returns untrusted text. A rule can only apply the right control if it knows which class it is looking at.

ACS's position, as we read it in [#153], is that `capability` can already name code execution, and that the open problem is that the field is optional. Making `capability` required and enumerated would address the second reason above. It would leave type, verb and domain combined in one string ([section 3.1](#31-acs-classifies-a-step-in-two-places)).

The model call is a separate case: ACS has no hook and no `capability` value for it.

### 5.3 Approval: a decision in ACS, a step in AAG

In AAG, an approval (by a human or by an automated check) is a step: `step.gate`. A policy that says "a human must approve first" requires that a `step.gate` appears on the path before the sensitive action. The harness emits the gate, like any other step. 

In ACS, the same intent is a decision. The Guardian returns `ask`, and an Approver is consulted. That consultation is not a hook.

In our view an approval is something that happens on the agent's path, whoever asked for it. Harnesses already run approvals that no Guardian asked for: a permission prompt in a coding agent, an interrupt in a workflow. ACS cannot see these today, so a Guardian cannot require one. 

We do not propose removing `ask` as a guardian output. Rather, we propose that every approval, however it came about, can be recorded as a step (proposal 4). A policy engine working on the path then needs only `allow` and `deny` from ACS: it denies the sensitive step until a gate has been recorded.

Two ACS decisions have no counterpart in AAG. `defer` describes a Guardian that has not reached a verdict; nothing happens on the agent's path while it waits. `modify` changes a step from the Guardian's side; this is not a behavior currently covered by AAG; in AAG's philosophy the Guardian is simple (and inspectable); complex changes to proposed tool calls should not be determined by a checkable Guardian.

### 5.4 ACS hooks without an AAG type

- **Turns.** ACS has three scopes: session, turn, step. A turn is one cycle of agent work inside a session — started by a user message, an auto-continuation, an agent loop, or a subagent returning — and context carries across turns. AAG has two scopes, task and step; the nearest counterpart of the ACS session is the task, and AAG has no turn level between the two. A turn that a user message starts is already visible in AAG as the `step.message GET` that received it, so a rule can find that boundary; a turn started by an auto-continuation or an agent loop is not marked. AAG also carries taint across the whole task, so ACS's own example — "deny consequential actions after a turn that retrieved untrusted data" — holds in AAG by default; what AAG cannot express is a per-turn count or limit, because it does not group steps into turns.
- **Compaction.** ACS attaches provenance to content. Compaction rewrites content, so ACS needs hooks around it to carry the provenance over. AAG records the path outside the model's context, so compacting that context does not change the path.
- **Skills.** Once a skill is loaded, its actions appear as ordinary steps. Registering or loading a skill has no dedicated AAG type today; it would be a `step.self` (the agent changing its own capabilities) or a `step.resource` (fetching a definition). A type of its own is optional, and something we might add ([section 7](#7-what-aag-can-take-from-acs)).

## 6. Discussions to extend ACS

We bring four proposals to ACS based on this mapping. We describe them here generically; more detail is in the discussion items on the ACS repo.

1. **A hook per class of action.** Code execution and access to secrets each get a hook of their own, so that the class is in the hook name ([section 5.2](#52-why-a-type-per-class-of-action)). A model call gets a hook, since ACS has none. The model-call part is a comment on the existing [#122] in the ACS repo; the other part relates to `tool_kind` in [#153].
2. **A closed field for the verb on tool calls.** `read`, `create`, `update` or `delete`, next to the existing `operation` field and not replacing it ([section 5.1](#51-verbs)). 
3. **`resource`, and a place for properties.** A `resource` field on tool calls, and an open object for further properties a harness can supply. This proposal also describes what proposals 1 to 3 together mean for `capability` ([section 3.1](#31-acs-classifies-a-step-in-two-places)). Related: [#8], which proposes trust and sensitivity metadata on tools and is deferred to ACS v0.2.0.
4. **Approvals as recorded steps.** A hook the harness emits when it has run an approval or a check itself, and an entry in the Guardian's record for every resolved `ask` ([section 5.3](#53-approval-a-decision-in-acs-a-step-in-aag)). Related: [#175] and Discussion [#115].

While reading ACS we also noticed that the three skill hooks are missing from its OpenTelemetry and OCSF mapping. ACS already tracks this ([#57], [#58]), so we do not raise it.

## 7. What AAG can take from ACS

The influence runs both ways. Each item below is a possible change to AAG and a question for [RFC-0001](../rfc/0001-agent-action-vocabulary.md).

| Possible change to AAG | What ACS shows |
|---|---|
| Value-level data lineage: which earlier values a value came from | ACS-Provenance's `derived_from` records this per content item. AAG instead assumes every earlier read in a task is potentially present in every later step (monotonic taint, `model.md` §3.1), so it does not track value-to-value lineage. Adding it would be a refinement, at a tracking cost to the harness |
| A type for registering and loading a skill | ACS has hooks for this ([section 5.4](#54-acs-hooks-without-an-aag-type)) |
| Marking which facts the harness observed, which it merely asserts, and which are cryptographically attested | AAG today trusts every step and property once a harness has emitted it. ACS names three levels — asserted, attached by framework code, attested (`docs/concepts/trust.md`). Worth improving; RFC-0001 has it as an open question |
| A hash link from each action to the previous one (we intend to add this to AAG) | ACS chains the entries of its session record this way, which makes the record tamper-evident |
| How a blocked action is recorded | ACS records the `deny` decision, and `toolCallResult` has an `exit_status` of `blocked`. RFC-0001 has this as an open question |
| A way to state the AAG version for a whole stream | The ACS handshake negotiates the version once per session. RFC-0001 has this as an open question |

## 8. Where the ACS schemas and prose differ

We tried to follow the schemas. Here are a few cases that seem ambiguous — prose on one side, schema on the other:

| Area | ACS prose | ACS schema | Tracked |
|---|---|---|---|
| `capability` shape | a string, independent of the tool (`concepts/capability.md`) | a string on `tool-call-request.json` and `agbom/component.json`, but a `{tool, operation, resource}` tuple in `agent-trigger.json` (`Intent.parsed`) and `ask-details.json` (`intent_extension`) | — |
| `toolCallRequest.tool` | `tool` (id, capability) (`hooks.md`) | `tool.name`, with `capability` a separate field (`tool-call-request.json`) | [#197] |
| `toolCallResult` id | `execution_id` (`hooks.md`) | `request_id_ref` (`tool-call-result.json`) | — |
| `signature` | REQUIRED in ACS-Core (specification §10) | optional (`request-envelope.json`) | [#195] |
| `acs_version` | top-level (specification §3) | inside `params` (`request-envelope.json`) | [#194] |
| `sessionEnd` reason | `session_reason` (`hooks.md`) | `reason` (`session-end.json`) | — |

This mapping will follow ACS as it develops.

[#8]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/8
[#57]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/57
[#58]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/58
[#115]: https://github.com/GenAI-Security-Project/agent-control-standard/discussions/115
[#122]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/122
[#153]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/153
[#175]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/175
[#194]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/194
[#195]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/195
[#197]: https://github.com/GenAI-Security-Project/agent-control-standard/issues/197
