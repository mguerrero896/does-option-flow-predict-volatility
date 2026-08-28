# Security policy

This is a research repository. It publishes code, tests,
aggregate results and hash pointers only; licensed granular market data is never
committed (see `data/DATA_ACCESS.md`).

## Reporting a vulnerability

Open a private security advisory on GitHub (Security → Advisories → Report a
vulnerability), which reaches the maintainer directly. Please do not open
a public issue for anything that could expose licensed data or credentials.

Scope of interest, in order:
1. Anything that could leak licensed granular data to the public mirror
   (the gated-publish and mirror contracts in `tests/` are the reference).
2. Anything that could compromise the sealed research programme (look counter,
   frozen artifacts, preregistration integrity).
3. Credential handling in provider scripts (`docs/reference/provider_http_reference.md`).

## Non-goals

The scientific methodology itself is documented and audited in-repo
(`docs/methodology_decisions.md`); disagreements with it are research
discussions, not vulnerabilities.
