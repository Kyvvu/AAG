# Changelog

All notable changes to the Agent Action Grammar are recorded here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the vocabulary
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- **A single action-type namespace.** All twelve action types now live under
  `step.`; the four that mark task boundaries are renamed `step.task_start`,
  `step.task_end`, `step.task_error`, and `step.task_idle`. Consumers that need
  to separate boundaries from actions match those four type names.

### Removed

- **The granularity axis, in full** — first the top-level
  `scopes: [task, step]` enumeration in
  [`spec/vocabulary.yaml`](spec/vocabulary.yaml), then the `granularity` block
  that briefly replaced it. With one namespace the projection is constant, so
  it classified nothing. The generator now rejects any action type outside
  `step.`.
- **The per-action-type `scope: task` / `scope: step` field.** It restated the
  type prefix and could only ever agree with it, so it was removed rather than
  renamed; the generator now rejects a source that carries it. The `(type, verb)`
  legality table is unchanged — granularity never separated a pair, which is the
  evidence it carried no information of its own. No emitted action ever carried
  the field, so the wire format is unaffected.

## [0.5.0] — draft

The first drafted version of the AAG, open for comment via
[RFC-0001](rfc/0001-agent-action-vocabulary.md).

### Added

- **Action types** — twelve, in a closed set: four `task.*` lifecycle types
  (`start`, `end`, `error`, `idle`) and eight `step.*` behavior types
  (`resource`, `message`, `self`, `model`, `credential`, `exec`, `gate`,
  `unknown`).
- **Verbs** — `GET` / `POST` / `PATCH` / `DELETE`, classified by data-flow intent
  rather than transport, with a per-type legality (`step.model`, `step.exec`,
  `step.gate`, `step.unknown`, and all `task.*` types take no verb).
- **Action anatomy** — positioning (`agent_id`, `task_id`, `seq`, `timestamp`,
  `step_name`; optional `parent_task_id`, `action_id`, `aag_version`),
  classification (`type`, `verb`), and content (the `properties` / `input` /
  `output` triplet). An absent `output` marks an *intended* action; a present one
  marks a *completed* action.
- **Suggested properties** — cross-cutting groups (`target`, `auth`, `data`,
  `agent`, `counterpart`; `transport` / `raw` as freeform envelopes) and their
  leaves. None are required; the tree is open.
- **Machinery** — [`spec/vocabulary.yaml`](spec/vocabulary.yaml) as the source of
  truth, projected to `vocabulary.json` and `action.schema.json`; a validator; a
  test suite; and the human specification ([`docs/model.md`](docs/model.md)) with
  an [OTLP mapping](docs/otlp-mapping.md) and an [adoption guide](docs/adoption.md).

<!-- Comparison/tag links are added once the first version is tagged:
[Unreleased]: https://github.com/Kyvvu/aag/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Kyvvu/aag/releases/tag/v0.5.0
-->

