# Contributing to the AAG

Thanks for helping build the Agent Action Grammar. This file covers the terms
and the mechanics; the *why* behind the process is in
[`GOVERNANCE.md`](GOVERNANCE.md).

## Licensing of contributions (inbound = outbound)

By contributing, you agree that your contribution is licensed under the same
terms as the part of the repository it touches:

- specification text, schemas, documentation, and examples — **CC BY 4.0**
  ([`LICENSE`](LICENSE));
- software — `spec/generate.py`, plus everything under `validator/` and
  `tests/` — **Apache-2.0** ([`LICENSE-CODE`](LICENSE-CODE)).

You retain copyright to your contribution; you simply license it to the project
and its users under those terms.

## Developer Certificate of Origin (DCO)

We use the [Developer Certificate of Origin](DCO) — a lightweight, paperwork-free
way to certify that you wrote, or otherwise have the right to submit, the code
you contribute. Sign off every commit:

```
git commit -s -m "your message"
```

which appends a line to the commit message:

```
Signed-off-by: Your Name <you@example.com>
```

That line certifies the DCO. No CLA is required.

## What needs an RFC, and what doesn't

- **Ordinary changes** — fixes, clarifications, examples, docs, and new
  *suggested* properties — go through a normal pull request.
- **Substantive changes** — anything touching the closed core (the action types,
  the verbs, the `(type, verb)` legality), the action fields, or the meaning of
  an existing term — go through the [RFC process](rfc/README.md).

## Making a change

1. Branch off a feature branch and open a pull request into `dev`.
2. If you touch the vocabulary, edit
   [`spec/vocabulary.yaml`](spec/vocabulary.yaml) — the single source of truth —
   and regenerate: `python spec/generate.py`. Never hand-edit `vocabulary.json`
   or `action.schema.json`.
3. Run the checks locally before opening the PR:

   ```
   pip install -r requirements-dev.txt
   ruff check .
   mypy spec validator tests
   python spec/generate.py --check
   pytest -q
   ```

   CI runs the same four checks on every pull request.

## Code of Conduct

Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By taking
part, you agree to uphold it.
