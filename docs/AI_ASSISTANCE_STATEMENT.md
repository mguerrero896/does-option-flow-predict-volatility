# Statement on computational assistance

**Author:** Miguel Guerrero. **Updated:** 2026-09-09.

AI coding assistants were used in the implementation of this research: to write
and review code, to draft and revise documentation, and to audit the repository
against its own contracts. This statement exists so that the disclosure is made
once, plainly, in the place a reader would look for it.

## Scientific responsibility

The author remains accountable for the study's claims, design decisions and
authorized access to evidence. Hypotheses, metrics, thresholds, registrations and
read permissions are recorded in the [methodology ledger](methodology_decisions.md).
The [current decisions](research_decisions_current.md) distinguish those records
from superseded plans. Tool assistance is not independent scientific validation.

## Why the distinction is checkable rather than asserted

The integrity of this study does not rest on who typed a line of code. It rests
on machinery that is public and runs on every commit:

- Registrations retain their dates, hashes and knowledge boundaries. RP4 v4 was
  fixed before its own calculation but reuses historical windows observed earlier;
  it is the fourth evaluation, not an independent prospective confirmation.
- Designated one-shot cohorts use access ledgers. Each cohort's actual disposition
  matters: Phase 8 was consumed, while prospective RP4 and RP3 outcomes remain future
  evidence. A general one-read label does not describe every historical comparison.
- Every published number traces to an artifact with a registered SHA-256, and a
  contract test fails if a frozen artifact is modified.
- A preregistered null is a valid outcome by binding rule, so there is no
  incentive — human or machine — to tune one away.

These controls help expose unauthorized changes and reporting errors. They cannot
by themselves prove model validity, eliminate implementation defects or recover
unavailable evidence. The [defect register](known_defects_and_resolutions.md) states
verified repairs and remaining limits.

## Reproducibility

The [reproduction guide](reproduce.md) provides public artifact checks and figure
regeneration. Full scientific reconstruction additionally requires licensed inputs,
their exact hashes and the registered execution context. Historical absolute-path
dependencies remain a documented portability limit.

## Attribution policy for commits

From 2026-08-26, author-created branch commits use GitHub's `noreply` address,
and assistant co-authorship trailers are not added. GitHub-generated squash
commits can carry the account-configured author email; the history scanner accepts
that identity only for a `web-flow`-signed commit on the published mainline. The
disclosure above is the deliberate, single place where computational assistance is
declared; a trailer on each of several hundred commits states the same fact worse.

Author-created commits before that date carry a personal address and, in some
cases, an assistant trailer. They are not rewritten: this repository does not
rewrite its own history to look tidier than it was, and the record of how the work
was actually produced is part of its evidence.

The [earlier statement](archive/public_refresh_baseline/docs__AI_ASSISTANCE_STATEMENT.md.original)
is retained as dated history; its general statements do not override these limits.
