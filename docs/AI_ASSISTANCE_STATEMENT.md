# Statement on computational assistance

**Author:** Miguel Guerrero. **Date:** 2026-08-26.

AI coding assistants were used in the implementation of this research: to write
and review code, to draft and revise documentation, and to audit the repository
against its own contracts. This statement exists so that the disclosure is made
once, plainly, in the place a reader would look for it.

## What that assistance did not decide

The scientific content of this work is the author's. Specifically, no assistant
chose a hypothesis, selected an evaluation metric, set a significance threshold,
decided when a protocol was frozen, or authorized a read of a sealed cohort.
Those are recorded as numbered methodology decisions in
`docs/methodology_decisions.md`, each with its rationale and its date, and every
one of them is the author's.

## Why the distinction is checkable rather than asserted

The integrity of this study does not rest on who typed a line of code. It rests
on machinery that is public and runs on every commit:

- Protocols are hash-sealed **before** their results are seen, so a result
  cannot retroactively change the question that was asked.
- Holdout samples are read **once**, under an access ledger.
- Every published number traces to an artifact with a registered SHA-256, and a
  contract test fails if a frozen artifact is modified.
- A preregistered null is a valid outcome by binding rule, so there is no
  incentive — human or machine — to tune one away.

An assistant operating inside those constraints cannot manufacture a finding,
and neither can the author. That is the point of the constraints.

## Reproducibility

The analysis is reproducible from this repository and the licensed data sources
named in the README, without any assistant.

## Attribution policy for commits

From 2026-08-26, commits use GitHub's `noreply` address rather than a personal
one, and assistant co-authorship trailers are not added. The disclosure above is
the deliberate, single place where computational assistance is declared; a
trailer on each of several hundred commits states the same fact worse, and
publishes a personal address alongside it.

Commits before that date carry a personal address and, in some cases, an
assistant trailer. They are not rewritten: this repository does not rewrite its
own history to look tidier than it was, and the record of how the work was
actually produced is part of its evidence.
