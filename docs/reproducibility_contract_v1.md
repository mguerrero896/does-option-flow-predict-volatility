# Reproducibility: scope and limits

**Status: CURRENT.** This maintained account clarifies the boundaries of the
original 18 August 2026 reproducibility contract. It does not replace historical
execution receipts or their hashes.

The repository contains substantive scientific source code, saved aggregate
evidence and provenance. **An independent, complete reconstruction of the current
study from a portable public clone has not been established.** Licensed-data
restrictions are one boundary; historical path bindings and execution custody are
additional boundaries. Public checks must not be presented as a substitute.

## Three distinct checks

| Route | Available evidence | Limit |
| --- | --- | --- |
| Public contract verification | Tracked artifacts, claim checks, source hashes and history/secret screening | Does not refit the reported study; does not run every test or measure coverage |
| Hermetic CI and synthetic demo | Unit, property and synthetic tests within the declared CI boundary | Skips and excluded licensed tests remain unverified; synthetic outcomes are not research results |
| Licensed scientific reconstruction | Original observations, frozen panels, recorded environment and execution receipts | Requires licensed access and valid custody; complete independent portable execution is not demonstrated |

Start with the cross-platform [public verification commands](reproduce.md).
The [CI workflow](../.github/workflows/ci.yml) defines the tested modules, coverage
threshold and exclusions. A threshold is not an observed result: cite the actual
run for its commit, pass/skip counts and measured coverage. Neither statement
means that every methodological unit or scientific failure mode has been tested.

## Synthetic demonstration

The [public demo](../scripts/run_public_repro_demo.py) is a **methodological smoke
test** using redistributable synthetic inputs. It exercises selected methodological
primitives, not the current RP4 acquisition, feature construction, model-fitting
and publication pipeline end to end. Its numbers provide no evidence about the
licensed observations or the size of the reported effect.

The container's allowlisted context excludes licensed-derived data and the full
evidence/documentation tree. It runs that demonstration, not the full suite:

```sh
docker build -t options-research-demo .
docker run --rm options-research-demo
```

## Licensed inputs and portability

The current RP4 results use FMP one-minute bars and Unusual Whales option records.
Massive was audited but does not supply the reported option-trade results; its
entitlement is not a prerequisite for reproducing those results.
See the [data access policy](../data/DATA_ACCESS.md) and
[historical execution guide](rp4/OPERATING_GUIDE.md).

Source, panel and environment hashes identify the recorded inputs; they do not
make missing data downloadable or prove an independent rerun. Public provenance
derivatives with redacted locators have separately recorded hashes. Some historical
supervisors obtain fixed roots from their frozen specifications and lack an
output-root override. Those bindings must not be silently changed, nor their
receipts deleted, to make an apparent rerun succeed.

The execution guide records the original commands, immutable receipts, remaining
portability limits and the checks actually performed. It explicitly reports that
a complete rerun from scratch was not performed in that review. A future clean
reconstruction would need its own checked input-to-output record; a green public
contract run cannot supply it. Closed one-shot evaluations and prospective cohorts
retain their separate authorization rules.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
