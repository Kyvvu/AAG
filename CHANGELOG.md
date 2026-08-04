# Changelog

All notable changes to the Agent Action Grammar are recorded here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the vocabulary
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

