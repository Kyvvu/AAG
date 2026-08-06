<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/aag-logo-dark.svg">
    <img src="assets/aag-logo-light.svg" alt="Agent Action Grammar (AAG)" width="360">
  </picture>
</p>

<p align="center">
  <strong>A small, open, versioned vocabulary for describing what an AI agent is actually doing.</strong>
</p>

<p align="center">
  <a href="https://github.com/Kyvvu/AAG/actions/workflows/ci.yml"><img src="https://github.com/Kyvvu/AAG/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <a href="rfc/0001-agent-action-vocabulary.md"><img src="https://img.shields.io/badge/RFC--0001-open%20for%20comment-6366f1" alt="RFC-0001: open for comment"></a>
  <a href="https://github.com/Kyvvu/AAG/discussions"><img src="https://img.shields.io/badge/GitHub-Discussions-6366f1?logo=github&logoColor=white" alt="GitHub Discussions"></a>
  <img src="https://img.shields.io/badge/version-0.5.0%20draft-8b5cf6" alt="Version 0.5.0 (draft)">
  <a href="LICENSE"><img src="https://img.shields.io/badge/spec-CC%20BY%204.0-64748b" alt="Spec licensed CC BY 4.0"></a>
  <a href="LICENSE-CODE"><img src="https://img.shields.io/badge/code-Apache%202.0-64748b" alt="Code licensed Apache-2.0"></a>
</p>

The AAG is a standard way to describe the actions an agent takes while carrying out a task. Every action carries

* a **type** (`task.start`, `step.resource`, `step.message`, …), 
* a **verb** where one applies (`GET`/`POST`/`PATCH`/`DELETE`, read as whether data enters or leaves the task — not as an HTTP method), and 
* a tree of **`properties`** (`data.classification`, `target.host`, …). AAG fixes these so any tool, framework, or platform describes what an agent does in the same terms.

Jointly these actions describe the full *path* an agent takes and provide the input for security relevant rules / policies that allow us to control what an agent actually does.

---

## Why a shared vocabulary

AAG's purpose is agent **security**: if every agent harness — whatever the framework, model, or vendor — emits its actions in this vocabulary, those actions can be secured uniformly — reasoned about and controlled by any security tool that understands the vocabulary, rather than one built for a specific stack. The same uniform stream can also feed into existing observability and governance systems (see [`docs/otlp-mapping.md`](docs/otlp-mapping.md)), but security is the aim of the AAG itself.

The AAG was created for two reasons:

1. **Agents choose their own path at run time.** A conventional application's control flow is mostly fixed at design time: you can theoretically read the code and enumerate what it can do. Conversely, an agent decides its next step by asking a model, while the task runs, not before. Whether individual actions are admissible is already covered by existing controls — access control, isolation. Also, the content flowing through an agent is often covered by guardrails. What neither of these covers is the *path* — the order in which individually-permitted actions are strung together at run time: a read here, a send there, each fine on its own, the combination a leak that no single step reveals. The formal case for treating that path, not the isolated action, as the object governed is set out in [*Runtime Governance for AI Agents: Policies on Paths*](https://arxiv.org/abs/2603.16586v1) (Kaptein, Khan & Podstavnychy, 2026).

2. **No two frameworks — or models — name the actions inside that path the same way.** This is annoying to say the least, as this fragmentation of vocabulary makes it impossible to specify security rules / policies that apply to all of your agents at once. The fragmentation starts before an agent framework (harness) is even involved: OpenAI returns a plan as `tool_calls`, Anthropic as `tool_use` content blocks, Gemini as `functionCall` with protobuf-derived types — three different shapes for the same event, straight from the model. MCP doesn't close this: MCP simply standardizes how tools are *described* and connected to a model, not how the model's resulting plan is executed by the harness. Every agent harness then adds its own layer on top of that — tool calls, spans, callbacks, traces — describing the same handful of underlying behaviours in yet more incompatible shapes. "The agent called an external API," "the agent read a secret," "the agent messaged the user" — there is no common word for any of these across OpenAI, Anthropic, or Gemini, let alone across commercial coding agents like Claude Code or Codex, and agent harness frameworks like LangChain or CrewAI, a custom harness. Without common words, a path built from actions named one way can't be compared to a path built from actions named another way, and every downstream tool — a log pipeline, an auditor, a policy engine — needs a separate adapter per model and per framework it wants to reason about.

AAG gives those behaviours one name each, so that:

- a **framework** can emit actions natively, without a per-vendor adapter;
- a **uniform set of rules** can be created which secures dangerous paths (or really "sets of paths") across all agents;
- a **downstream security tool** — a policy engine or auditor — can consume actions from any source in the same shape and secure them;
- a **reviewer or auditor** can read an action stream without knowing which framework produced it.

## The AAG standardizes actions, it does not operate on them 

The AAG is a grammar, not a security engine. This means that:

- It defines what an agent action *is* — a closed set of action types and verbs, plus an open, namespaced tree of properties.
- It does **not** define whether an action is *allowed*. No policies, no rules, no data-exfiltration checks, no enforcement. That would be the job of a policy engine, and is out of scope here (though it's exactly the kind of application the AAG is meant to make possible).

Thus, in its bare essence, the AAG is designed to allow building more secure agents. The closed vocabulary provided by the AAG is an alphabet that security policies and rules can be written against — the AAG supplies the words; an engine can do policing, uniformly, across agents. 

If you have used OpenTelemetry: AAG is to agent security what OTel's semantic conventions are to observability. OTel opened the observability data model and let vendors compete on the backend. The AAG opens the agent-action vocabulary; security engines, audit trails, and compliance mappings can compete behind it. However, we need some standardization to make all of this work across the board, for all our agents.

## Nearby efforts

Several efforts sit close to the AAG so it's worthwhile highlighting these specifically:

- **OpenTelemetry's GenAI semantic conventions** define agent lifecycle spans (`create_agent`, `invoke_agent`, `execute_tool`) and MCP conventions. They are an observability schema: span names are an open surface, and a span is by construction a record of something that happened. The AAG differs on the three points which any security rules or policies would depend on: 1. The AAG provides a *closed* enum, 2. the AAG provides verbs that classify an action by its actual data flow rather than record what the tool interface claimed, and 3. the AAG provides an *intended* form that describes an action before it executes. Hence, the two compose rather than compete; in [`docs/otlp-mapping.md`](docs/otlp-mapping.md) we map the AAG actions onto OTLP for observability after the agent-task is done.
- **OWASP's Agent Observability Standard (AOS)** extends OpenTelemetry and OCSF with agent-specific events rather than defining a vocabulary of its own — a reasonable position for observability and for catching up with our agentic world, but it inherits the same caveats that are needed for security: we need fixed names, data relevant semantics, and a preventative representation.
- The **Agent Control Standard (ACS)** is in a way the nearest neighbor: it targets *runtime control* and hence it comes with runtime hooks, inline policy enforcement, and an explicit EU AI Act human-oversight motivation; this would be goals that any user of the AAG can pursue. However, ACS again provides an open vocabulary and does not contain -- in our view -- the security relevant semantics necessary to fully cover agent workflows. Also, in our view, it erroneously singles out human approval as singular; based on experience in many production systems, we treat human approval as just a "gate" with specific properties; a gate which might be required within a task and thus has to be enforced by some rule.
- **AGNTCY's OASF** describes agents — their capabilities and metadata — not the actions they take at run time. The two are complementary: OASF says what an agent *is*, the AAG says what it *is doing*.

You can find the sources for each of the above here:

* [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
* [OWASP Agent Observability Standard (AOS)](https://owasp.org/www-project-agent-observability-standard-2/)
* [Agent Control Standard (ACS)](https://agentcontrolstandard.org/)
* [AGNTCY OASF](https://docs.agntcy.org/oasf/open-agentic-schema-framework/)

> Note that there is also an active agent policy discussion in the academic world (see for example [AgentSpec](https://arxiv.org/abs/2503.18666), [Progent](https://arxiv.org/abs/2504.11703), our own [*Runtime Governance for AI Agents: Policies on Paths*](https://arxiv.org/abs/2603.16586), and others). These works often detail how theoretically rules and policies should be shaped, but often simply pre-suppose some underlying jargon (or simply view it as a trivial engineering problem -- which it is, but someone has to do it). 

## The shape of the vocabulary

The AAG is composed of two main layers:

1. **A closed enum table.** Every agent-action is one `(type, verb)` combination drawn from a fixed, versioned allow-list. These are the nouns and verbs of the language, and they do not change without a version bump.

   | type              | verbs                  | meaning (abridged)                          |
   |-------------------|------------------------|---------------------------------------------|
   | `task.start`      | —                      | a task run begins                           |
   | `step.resource`   | GET/POST/PATCH/DELETE  | read or write a resource                    |
   | `step.message`    | GET/POST               | receive from / send to whoever the agent is interacting with |
   | `step.model`      | —                      | invoke a model                              |
   | `step.credential` | GET/POST/PATCH/DELETE  | read or write a secret/credential           |
   | …                 | …                      | see [`spec/vocabulary.yaml`](spec/vocabulary.yaml) |

2. **An open properties tree.** Beyond type and verb, an action may carry a nested `properties` object. The AAG suggests a number of cross-cutting groups (`target`, `auth`, `data`, `agent`) with defined meanings but leaves the rest open — no property is required, and an emitter may add its own. The enums are closed; the properties tree is open and extensible.

> Note that it is foreseeable that at some point a number of properties will become required.

The canonical source of truth is **[`spec/vocabulary.yaml`](spec/vocabulary.yaml)**. A human readable version including a discussion of its semantics is found in [`docs/model.md`](docs/model.md). A machine-readable **[`spec/vocabulary.json`](spec/vocabulary.json)** is generated from the `yaml`, and the **[`spec/action.schema.json`](spec/action.schema.json)** is the JSON Schema for a single emitted action. 

## Repository layout

```
spec/         The vocabulary itself in machine and human (assuming you are ok reading `yaml` files) format.
docs/         The semantics (what each type/verb means), some pointers on how to use the AAG, and a mapping to OTLP.
examples/     A set of complete example tasks, both properly and improperly formatted.
validator/    A tiny, dependency-light checker: is this a well-formed AAG action? Is this a well-formed task?
tests/        A simple script to see if every example validates (or fails) as intended.
rfc/          The request-for-comments driving this standard forward
```

## Quick look — a single action

```json
{
  "agent_id": "invoice-assistant",
  "task_id": "run-2f1c",
  "timestamp": "2026-07-30T09:14:22Z",
  "type": "step.resource",
  "verb": "POST",
  "step_name": "post_invoice",
  "input": { "invoice_id": "INV-2026-0917", "customer_id": "C-4821", "amount": 148.00, "currency": "EUR" },
  "output": { "status": "created", "id": "inv_9f2a17" },
  "properties": {
    "target": { "trust": "external", "host": "api.billing.example.com" },
    "data":   { "classification": "pii" }
  }
}
```

Validate it:

```bash
python validator/validate.py examples/actions/step_resource_post.json
```

## Adopting the AAG

No particular SDK is required to emit actions according to the grammar. Simply produce JSON that validates against [`spec/action.schema.json`](spec/action.schema.json) and follows the semantic conventions in [`docs/model.md`](docs/model.md). See [`docs/adoption.md`](docs/adoption.md) for examples of AAG implementations. 

## Working with AAG formatted actions upstream

The AAG is created for securing an agent while it's going about its job. When done, it is reasonable to log the actions (and associated security rules or policies). This is easy using the simple mapping to OTLP presented in [`docs/otlp-mapping.md`](docs/otlp-mapping.md).

## Versioning & stability

AAG is semver-versioned. The enum table is a compatibility surface: adding a type or verb is a minor bump, removing or repurposing one is a major bump. Reserved property groups follow the same discipline; custom groups are yours and should never break. See [`CHANGELOG.md`](CHANGELOG.md) for changes along the way.

## Governance

This repository is currently maintained by a number of [Kyvvu](https://www.kyvvu.com) team members — Maurits Kaptein and Andriy Podstavnychy are the people actively stewarding it. This is a starting point, not at all the intended end state: the AAG should grow into a vocabulary held by a structured body of contributors, with regular open meetings and shared control over the vocabulary, rather than staying a single company's repository that happens to be public. 

How that structure is reached — including envisioned membership, decision-making, meeting cadence — is described in [`GOVERNANCE.md`](GOVERNANCE.md) (and updated as it takes shape).

**Contributing.** Branch off a feature branch, open a pull request into `dev`. The full contribution and governance process is documented in [`GOVERNANCE.md`](GOVERNANCE.md), but that's pretty much it. Questions and general discussion happen in [GitHub Discussions](https://github.com/Kyvvu/AAG/discussions).

The vocabulary itself is licensed CC-BY-4.0, independent of who maintains the repository — so it can outlive whoever stewards it today. Proposals and disagreements about the vocabulary go through the [RFC process](rfc/README.md).

## License

The repository is dual-licensed:

- the **specification, schemas, documentation, and examples** under **CC BY 4.0** — see [`LICENSE`](LICENSE);
- the **software** (`spec/generate.py`, plus everything under `validator/` and `tests/`) under **Apache-2.0** (which carries an explicit patent grant) — see [`LICENSE-CODE`](LICENSE-CODE).