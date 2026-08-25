# AAG examples

Concrete examples, split by what they are:

- **`actions/`** — single actions, one JSON object per file.
- **`tasks/`** — whole tasks, one action per line (a [JSON Lines](https://jsonlines.org/) stream, `.ndjson`).

Every file here is checked by the test suite against
[`../spec/action.schema.json`](../spec/action.schema.json): the valid actions
must pass, the `invalid_*` ones must fail.

## Single actions — `actions/`

| file | what it shows |
|------|---------------|
| [`step_resource_post.json`](actions/step_resource_post.json) | A **completed** external write (POST to a billing API), with an `output`. |
| [`step_resource_get.json`](actions/step_resource_get.json) | A **completed** internal read of a customer record. |
| [`step_resource_get_intended.json`](actions/step_resource_get_intended.json) | The **intended** form of the same read — no `output`, no `seq` — as a pre-execution hook would emit it. |
| [`step_credential_get.json`](actions/step_credential_get.json) | A `step.credential` GET (reading a secret from `.env`) — note the secret value stays out of `output`, only `data.classification: secret`. |
| [`step_self_post.json`](actions/step_self_post.json) | A `step.self` POST — the agent writing to its own memory (state that may outlive the task). |
| [`step_exec.json`](actions/step_exec.json) | A `step.exec` — code execution; the `command` is a bare, type-scoped leaf. |
| [`step_task_start.json`](actions/step_task_start.json) | A `step.task_start` carrying agent context (`agent.*`) and `aag_version`. |
| [`step_task_idle.json`](actions/step_task_idle.json) · [`step_task_error.json`](actions/step_task_error.json) | The `step.task_idle` and `step.task_error` lifecycle markers. |
| [`step_gate.json`](actions/step_gate.json) | A `step.gate`. Its decision (`pass`/`deny`) is the action's **`output`**; `input` is what was checked; `kind` (human/guardrail) is a property. |

### Invalid (must fail)

| file | why it is malformed |
|------|---------------------|
| [`invalid_step_model_with_verb.json`](actions/invalid_step_model_with_verb.json) | `step.model` is a verbless type (a model call is both a source and a sink), so carrying a `verb` is not a legal `(type, verb)` combination. |
| [`invalid_step_task_start_with_verb.json`](actions/invalid_step_task_start_with_verb.json) | The lifecycle types take no verb; a `step.task_start` carrying a `verb` is malformed. |
| [`invalid_unknown_type.json`](actions/invalid_unknown_type.json) | `type` must be one of the twelve; `step.frobnicate` is not in the closed set. |

## Tasks — `tasks/`

The AAG specifies a single **action**. It does not define a task-file format — a
task is simply every action that shares one `task_id`.

- [`support_ticket.ndjson`](tasks/support_ticket.ndjson) — a full task, from
  `step.task_start` to `step.task_end`: the support agent receives a billing question,
  calls the model to plan (which returns a tool call), reads the customer record
  (pulling `pii` into the task), calls the model to compose an answer, passes an
  exfiltration-review gate, and replies to the user.
- [`subagent_handover.ndjson`](tasks/subagent_handover.ndjson) — a **sub-agent**
  task with its own memory: `step.task_start` links back to the parent via
  `parent_task_id`, the brief arrives as a `step.message` GET carrying
  `counterpart.kind: parent_agent` (**untrusted** — the parent is not the human
  user), the sub-agent fetches public docs, and returns the result to the parent.

The task here is **NDJSON** — one action per line — the natural shape for an
append-only log where each action is emitted the moment it happens. A JSON array
(`[ … ]`) is an equivalent batch representation of the same task; the AAG
mandates neither.
