# RFC-0001 — Introducing the Agent Action Grammar

> **Status:** Draft — open for comment.
> **Full specification:** [`../docs/model.md`](../docs/model.md) · **Machine-readable:** [`../spec/vocabulary.yaml`](../spec/vocabulary.yaml)

## The problem

An AI agent chooses its next step at run time, by asking a model. Unlike a
conventional program — whose control flow you can read off the source and
enumerate — you cannot know ahead of time what an agent will do. Individual
actions are already guarded: access control, isolation, content guardrails. What
is *not* guarded is the **path** — the order in which individually-permitted
actions are strung together. A read here, a send there; each fine on its own, the
combination a leak that no single step reveals.

However, every framework and model describes that path in its own shapes — OpenAI
`tool_calls`, Anthropic `tool_use` blocks, Gemini `functionCall`, and a further
layer per harness on top. There is no shared word for "the agent read a secret"
or "the agent messaged the user," so a single security policy cannot be written
once and applied across a fleet of diverse agents. 

> **This is a request for comments — the whole point is to hear back.** We're circulating RFC-0001 to gather reviews, remarks, and — we hope — contributors. If something here reads as wrong, incomplete, or hard to adopt in your own harness, that is exactly what we want to know. To weigh in, comment in the **[RFC-0001 feedback thread](https://github.com/Kyvvu/AAG/discussions/3)** — or anywhere in [GitHub Discussions](https://github.com/Kyvvu/AAG/discussions) — or open an [issue](https://github.com/Kyvvu/AAG/issues/new) referencing `RFC-0001`.

## The proposal

The **Agent Action Grammar (AAG)** is a small, closed vocabulary for what an agent
*does*. If every harness emits its actions in this vocabulary, security tooling
can reason over agent behaviour uniformly — whatever the framework, model, or
vendor.

AAG **describes**; it does not **enforce**. It is the alphabet that security
policies can be written against — not the policies themselves. However, using
the concept of *intended* actions, it is deliberately designed to facilitate
real-time security policies that intervene in an agent's path at runtime.

The AAG considers an agent's work to be composed of multiple tasks. 
A new **task**, which is the boundary between data in memory, opens with
`step.task_start`, runs a stream of steps, and closes with `step.task_end`. 

Every record — lifecycle marker or `step` — is an **action**.

## The vocabulary

### Action types: security meaningful action classifications

| type | what it is |
|------|-----------|
| `step.task_start` · `step.task_end` | a task opens · closes |
| `step.task_error` · `step.task_idle` | a task fails (may resume) · pauses |
| `step.resource` | read or write a resource or tool — the workhorse |
| `step.message` | receive from / send to whoever the agent is talking to |
| `step.model` | invoke a model |
| `step.self` | read or write the agent's own memory |
| `step.credential` | read or write a secret or credential |
| `step.exec` | run code |
| `step.gate` | a guardrail or a human approval |
| `step.unknown` | an action that could not be classified |

### Verbs: data flow to and from the agent

A step carries a **verb**, read as the *direction of data*, not the transport
method:

| verb | meaning |
|------|---------|
| `GET` | data enters the task |
| `POST` | task data leaves, or external state is created |
| `PATCH` | external state is modified |
| `DELETE` | external state is removed |

So a `GET` that smuggles data outward through a large query string should, in AAG, be a
`POST`. Some types take no verb: `step.model` is both a source and a sink;
`step.exec`, `step.gate`, and all `task.*` carry none.

### Properties

Beyond type and verb, an action carries an open `properties` tree. None are
required; AAG *suggests* the recurring, security-relevant ones — `target.trust`,
`target.host`, `data.classification`, `counterpart.*`, `agent.*` — so they are
named the same way everywhere.

### Anatomy of an action

An action is one JSON object in three layers:

- **positioning** — `agent_id`, `task_id`, `seq`, `timestamp`, `step_name`;
- **classification** — `type`, and (where the type takes one) `verb`;
- **content** — `properties` (the security-relevant metadata), `input`, `output`.

One of the core features of the AAG is the notion of an intended action: **an action with no `output` is *intended*** —
described *before* it executes, so a security layer can allow or deny it before
any effect. An action *with* an `output` is considered *completed*. 

The pre-execution object, the intended action, is exactly what an observability span — a record of something that already
happened — cannot (and should not) represent.

Here is a simple example of an AAG formatted *intended* action as it can be emitted by an agent harness:

```json
{ "agent_id": "support-assistant", "task_id": "run-9f2ac1", "seq": 3,
  "timestamp": "2026-07-30T09:14:23Z", "step_name": "get_customer_record",
  "type": "step.resource", "verb": "GET",
  "properties": { "target": { "trust": "internal", "host": "crm.internal" },
                  "data": { "classification": "pii" } } }
```

A policy could read that in one line to mean an *internal* read that pulled *pii* into the
task. If, later in the same task, it is followed by a `step.resource POST` to an
*external* host, you have an exfiltration path that the AAG exists to make actionable.

### The memory model

Within one task, any data a step reads is assumed available to every later step;
a new task starts from a blank slate. That single assumption is what lets a policy
reason about the whole *path* — a source, then a sink — rather than isolated
steps. (A more formal argument is in *[Runtime Governance for AI Agents: Policies on
Paths](https://arxiv.org/abs/2603.16586)*.)

## What AAG is not

- **Not an engine.** No policies, no rules, no enforcement — that is a policy
  engine's job. It's just a language describing what an agent is doing as it goes.
- **Not observability.** It maps cleanly to OpenTelemetry (an
  [OTLP mapping](../docs/otlp-mapping.md) is provided) but adds two things a
  span cannot carry: a *closed* vocabulary and the *intended* action jargon.

## Nearby efforts

- **[OpenTelemetry's GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai)**, and **[OWASP AOS](https://owasp.org/www-project-agent-observability-standard-2/)** / the **[Agent Control
  Standard (ACS)](https://agentcontrolstandard.org/)** that extend OpenTelemetry and OCSF, are observability schemas
  with an open surface. None defines a closed action enumeration, an
  intended/completed distinction, or a task-memory model — the parts a security
  policy is written against.
- **[AGNTCY's OASF](https://docs.agntcy.org/oasf/open-agentic-schema-framework/)** describes what an agent *is* (capabilities, metadata); AAG
  describes what it *did*. The two are complementary.

## How to comment

Comment via this repository's **[GitHub Discussions](https://github.com/Kyvvu/AAG/discussions)**, or open an [issue](https://github.com/Kyvvu/AAG/issues/new) referencing
`RFC-0001`. Feedback is most useful on:

- whether the twelve types and their verb legality carve agent behaviour at the
  right joints;
- the open questions below;
- anything that would stop your harness or engine from adopting AAG.

Substantive changes land through the [RFC process](README.md), with a version bump
and a [`../CHANGELOG.md`](../CHANGELOG.md) entry.

## Open questions

These are the points not yet settled, each with the currently preferred
direction.

### Fixed properties

Should any properties be reserved, fixed, or required? Today none are — the property tree is entirely open (see `model.md` §2.4), which maximizes adoption but means two emitters can describe the same situation with different keys. **Preferred direction:** keep properties open while the standard is young and, as usage converges, promote a few leaves (for example `target.trust` and `data.classification`) from *suggested* to *required for the action types where they are meaningful*. Freezing too early risks standardizing the wrong vocabulary; freezing too late risks fragmentation. The trigger for pinning a property should be evidence that it is widely emitted and relied upon — not a guess made now.

### Input / output granularity

What exactly goes in `input` and `output`? For a `step.model`, is `input` the full prompt and `output` the full completion? Recording everything is the most complete, but it turns the audit log into a copy of every piece of data the agent ever touched — a significant confidentiality and storage burden. **Preferred direction:** `input`/`output` are optional and may hold a *summary or reference* (a hash, a token count, a redacted view) rather than raw content. The AAG's classification never depends on them (`model.md` §3.1), so an emitter that needs full fidelity can store it, and one that needs privacy can omit or summarize it — without changing the meaning of the action.

### Recording blocked actions

When a pre-execution check denies an intended action, how is that recorded? In the intended/completed model (`model.md` §2.2) a denied action is naturally an intended record that never gains an `output` — but that is indistinguishable from one still pending, or simply never followed up. **Preferred direction:** a blocked action should leave a *visible, unambiguous* trace rather than a silent gap: the intended record, carrying an `action_id`, followed by a matching terminal record that repeats the `action_id` — either the action re-emitted with an `output` marking the denial, or a `step.task_error` if the denial halts the task. The exact shape of the denial `output` is unsettled; what matters is that "was blocked" and "never happened" are not confusable in a log.

### Versioning: out-of-band negotiation

The in-band mechanism is specified: `step.task_start` may carry `aag_version`, and semantic versioning applies to the vocabulary so a consumer can distinguish a compatible minor addition from a breaking change. What remains open is **out-of-band agreement** — whether a channel-level declaration (a header, an OTLP resource attribute) should be defined for streams whose `step.task_start` an intermediary never sees.

### A verb for `step.exec`

`step.exec` takes no verb, so the harm axis (`model.md` §2.3) cannot reach it: a policy that forbids the `DELETE` class outright does not catch `rm -rf /`, the very example in the `command` property. The current rationale is opacity — the harness generally cannot know what a command will read, write, or destroy without executing it. **Preferred direction:** keep the verb absent as the honest default, and consider an *optional* verb on `step.exec` for harnesses that do know (a sandboxed interpreter with a read-only mount, a declared dry-run). An emitter that asserts a verb it cannot verify would undermine the classification — which is the concern the next question generalizes.

### Asserted vs. verified properties

`model.md` §3.1 keeps classification independent of the model's words; nothing yet marks which *properties* the harness knows versus asserts. `target.host` is typically observed by the harness that made the call; `data.classification: pii` is often a label the emitter chose; `target.trust` may be either, depending on whether it comes from a network boundary or a config file. A consumer applying a policy to these values currently cannot tell the difference. **Preferred direction:** leave the property values as they are and consider a provenance marker per group or leaf (observed / configured / declared), promoted only if usage shows policies genuinely branch on it — the same evidence bar as *Fixed properties* above.

### Sub-agent / multi-agent representation

`model.md` §3.4 gives the AAG's *suggested* handling: a task is a shared-memory scope, so shared-memory sub-agents are one task (multiple `agent_id`s), and a hand-over to an agent with its own memory is a new task linked by `parent_task_id`, with the hand-over expressed as a `step.message` carrying `counterpart` trust. **Open:** whether this is the right or only model, and whether the `counterpart` trust marking should be *required* on a hand-over rather than suggested.
