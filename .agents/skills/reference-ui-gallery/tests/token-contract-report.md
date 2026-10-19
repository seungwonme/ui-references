# Token contract verification

## Scope

Candidate: reference-ui 0.6.0. This report covers deterministic token validation, CSS conversion, bundle execution and a narrow browser regression check. It does not establish full DTCG conformance or a model's skill-routing behavior.

## Before and after

- The new regression cases failed 16 assertions against 0.5.2 before implementation.
- The reviewed implementation passed 47 unittest cases, including all 13 DTCG value types, malformed values, inherited/resolved values, missing/cyclic aliases, schema tampering, native metadata and CSS font keywords.
- The full check passed for Aside (90 tokens), Apple web (42) and Apple app UI (57): 189 tokens retained.
- The same check ran through the generated project wrapper, without relying on an installed global skill or personal gallery configuration.
- The full suite also ran with the CI environment flag enabled. The local draft fixture isolates that flag in its own subprocess; the explicit CI draft-rejection case remains enforced.
- The baseline Apple app input is rejected for its extra native unit fields. The repair preserves numeric values and moves logical point metadata into an extension.
- The schema resource is bundled without changes and its SHA-256 is checked before use. A validation test forbids socket connection attempts.

## Browser regression

Aside compared fresh baseline and candidate builds at 390 and 1440 CSS px for all three previews. All six comparisons had equal heading dimensions, no horizontal overflow and no captured JavaScript errors. The CSS generic family remains unquoted in the candidate. These observations cover font/layout preservation; interaction QA, native optical fidelity and other color modes were not rerun. Mobile screenshot tiles were unreliable and were excluded from visual acceptance; the mobile result is a DOM/computed-style measurement.

## Reproduce

Run the gallery wrapper's check command from the checkout, as documented in the package contract. It runs the regression tests and actual package/schema/alias/CSS checks, then builds into a temporary directory that it removes. The uv invocation ignores machine-level configuration so the same lock is accepted in clean CI. The pinned Python lock travels with the standalone runtime and project skill. The complete project skill runs the full suite; the minimal CI runtime runs the token-contract suite and records the actual suite/count. An empty test bundle is rejected. CI repeats this check before building the Pages artifact.

## Limits and review

The supported alias profile rejects root tokens, group inheritance, JSON Pointers and array alias flattening explicitly. Google-compatible YAML export and external consumer imports are not implemented or certified by this change. The DESIGN document remains the package's prose usage contract.

No new-context model agent or additional CLI agent was started for this verification. Eval cases 10-12 cover malformed values, unsupported references and Google format claims, and are prepared but not model-executed here. The deterministic tests are not a substitute for model behavior evaluation. Global installation, a merge and a public Pages deployment require their own verification after approval.
