# Governance

This document describes how the Agent Action Grammar (AAG) is maintained and how
it changes. It is a starting point, and — like the vocabulary itself — is
expected to evolve.

## Who maintains the AAG

The AAG is currently stewarded by **Maurits Kaptein** and **Andriy Podstavnychy**,
with the support of the [Kyvvu](https://www.kyvvu.com) team, which builds a
security engine that speaks AAG.

It is not the intended end state. The AAG should grow into a vocabulary held by a
structured body of contributors — with regular open meetings and shared control
over the vocabulary — rather than a single company's repository that happens to
be public. How that body is formed (membership, decision-making, cadence) will be
worked out and recorded here as it takes shape. The specification is licensed
[CC BY 4.0](LICENSE) and the software [Apache-2.0](LICENSE-CODE), precisely so
that the standard can outlive whoever stewards it today.

While the AAG is stewarded by the two of us, an RFC is decided by the stewards
seeking rough consensus among the people who engaged with it; a decision and its
rationale are recorded in the RFC. As the contributor base grows, this interim
rule will be replaced by whatever the community body adopts.

## What is open, and what is stable

Not every part of the AAG changes at the same rate. This matters for governance,
because it determines what a change costs.

- **The closed core** — the twelve action types, the four verbs, and the
  `(type, verb)` legality (see [`spec/vocabulary.yaml`](spec/vocabulary.yaml)).
  This is a compatibility surface. Adding a type or verb is a minor version bump;
  removing or repurposing one is a major bump. Changes here require an RFC (below).
- **The action fields** — the closed set in the anatomy
  ([`docs/model.md`](docs/model.md) §2.2). A new field is a considered addition
  and needs an RFC.
- **The open properties tree** — no property is required, and an emitter may add
  any group or leaf. *Suggesting* a new leaf, or documenting one already in use,
  is an ordinary pull request, not an RFC.

## How changes are made

- **Ordinary changes** — fixes, clarifications, examples, docs, and new
  *suggested* properties — go through a normal pull request. Branch off a feature
  branch and open a PR into `dev`.
- **Substantive changes** — anything touching the closed core, the field set, or
  the meaning of an existing term — go through the [RFC process](rfc/README.md):
  a short proposal, discussion, and a decision recorded in the RFC. The
  specification stays focused on what *is* decided; open questions live in the
  RFCs.

The canonical source of truth is [`spec/vocabulary.yaml`](spec/vocabulary.yaml);
`vocabulary.json` and `action.schema.json` are generated from it and must not be
hand-edited. Every change is expected to pass the repository's checks (lint,
types, schema-is-up-to-date, tests).

The contribution terms — inbound = outbound licensing and DCO sign-off — and the
full local workflow are in [`CONTRIBUTING.md`](CONTRIBUTING.md). Participation is
governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Versioning

The vocabulary follows [Semantic Versioning](https://semver.org/). Notable
changes are recorded in [`CHANGELOG.md`](CHANGELOG.md).
