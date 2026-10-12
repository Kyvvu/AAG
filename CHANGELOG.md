# Changelog

All notable changes to the Agent Action Grammar are recorded here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the vocabulary
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.0] — draft

### Changed

- **Breaking: the action field `type` is renamed `kind`**, and the vocabulary key
  `action_types` in [`spec/vocabulary.yaml`](spec/vocabulary.yaml) (and the
  generated `vocabulary.json`) is renamed `action_kinds`. `type` collides with the
  JSON Schema keyword and the Python builtin, and most payloads a harness maps
  from carry a `type` of their own; `kind` also reads correctly for the `task.*`
  lifecycle markers, which are not steps. This is a hard cut with no alias: `kind`
  is required, and an action that carries `type` is rejected by the schema, whose
  top-level field set is closed
  ([`examples/actions/invalid_type_field.json`](examples/actions/invalid_type_field.json)).
  The prose follows: action kinds, `(kind, verb)`, kind-scoped leaves. The OTLP
  mapping emits the field as the span name plus `aag.kind`. The bare property leaf
  `kind` on `step.gate` and `counterpart.kind` are unchanged.
  ([#12](https://github.com/Kyvvu/AAG/issues/12),
  [Kyvvu/platform#602](https://github.com/Kyvvu/platform/issues/602))
- **The OTLP mapping keeps the `properties` prefix.** A grouped property
  `properties.<group>.<leaf>` maps to `aag.properties.<group>.<leaf>` and a bare
  leaf to `aag.properties.<leaf>`, instead of `aag.<group>.<leaf>` and
  `aag.<leaf>`. Properties are open, so the old mapping let a property overwrite
  the attributes for the action's own fields (`aag.verb`, `aag.kind`, …) or the
  suggested `aag.policy.*` results; those are now reserved
  ([`docs/otlp-mapping.md`](docs/otlp-mapping.md),
  [#11](https://github.com/Kyvvu/AAG/issues/11)).
- **Granularity replaces "scope" and is now explicitly derived.** The task-vs-step
  distinction is named **granularity** (values `task` / `step`, unchanged) and is
  documented as a projection of the action-kind namespace — read off the `kind`
  prefix — rather than an axis of the vocabulary in its own right.

### Removed

- **The top-level `scopes: [task, step]` enumeration** in
  [`spec/vocabulary.yaml`](spec/vocabulary.yaml), replaced by a `granularity`
  block that states the derivation rule alongside the two values.
- **The per-action-kind `scope: task` / `scope: step` field.** It restated the
  kind prefix and could only ever agree with it, so it was removed rather than
  renamed; the generator now rejects a source that carries it. The `(kind, verb)`
  legality table is unchanged — granularity never separated a pair, which is the
  evidence it carried no information of its own. No emitted action ever carried
  the field, so the wire format is unaffected.

### Fixed

- **`task.error` is described as reaching an abnormal state**, not as having
  "terminated abnormally" — the same paragraph already said the task may resume
  afterwards, so the two readings contradicted each other.
- **An implementer's note records a known schema gap**:
  [`spec/action.schema.json`](spec/action.schema.json) does not reject an
  `input` or `output` on a `task.*` lifecycle marker, though
  [`docs/model.md`](docs/model.md) §2.2 normatively forbids both. The prose is
  authoritative; the generated schema is a partial check of it.

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
[Unreleased]: https://github.com/Kyvvu/aag/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/Kyvvu/aag/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Kyvvu/aag/releases/tag/v0.5.0
-->

