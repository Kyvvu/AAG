# RFCs

Substantive changes to the AAG — anything touching the closed core (the action
types, the verbs, the `(type, verb)` legality), the action fields, or the meaning
of an existing term — go through a request for comments. The specification stays
focused on what *is* decided; the open questions and the reasoning behind them
live here.

Ordinary changes (fixes, clarifications, examples, docs, and new *suggested*
properties) do not need an RFC — open a pull request. See
[`../GOVERNANCE.md`](../GOVERNANCE.md) for the split.

## The RFCs

- [`0001-agent-action-vocabulary.md`](0001-agent-action-vocabulary.md) — the open
  design questions for the initial vocabulary. Effectively our starting call.

## Proposing one

1. Copy the numbering: the next free `NNNN-short-title.md`.
2. State the motivation, the proposal, the alternatives considered, and — where
   it is not yet settled — the currently preferred answer.
3. Open a pull request. Discussion happens on the PR; the decision is recorded in
   the RFC, and any resulting change to the vocabulary lands in
   [`../spec/vocabulary.yaml`](../spec/vocabulary.yaml) with a version bump and a
   [`../CHANGELOG.md`](../CHANGELOG.md) entry.
