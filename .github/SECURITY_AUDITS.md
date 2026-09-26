# H-11 security audit gate

`.github/workflows/security-audit.yml` checks both Python requirements files with pinned `pip-audit`, both tracked npm lockfiles with `npm audit --package-lock-only`, and all Git history with pinned gitleaks. It runs on main/security-hardening pushes, PRs into main, manual dispatch, and weekly. Network or malformed scanner responses fail closed. Gitleaks uses redacted error-level output; do not paste findings or tokens into issues or logs. Rotate/revoke any actual exposed credentials and remove them from history using a coordinated response.

## Reproduce

On Python 3.11 and Node 20, at repository root:

```sh
python -m pip install 'pip-audit==2.10.1'
python .github/scripts/security_audit.py python services/digital-brain/requirements.txt services/rpa-worker/requirements.txt
python .github/scripts/security_audit.py npm apps/web-console services/digital-brain/apps/web-console
```

For full history secret scanning on Linux, install the pinned gitleaks release used by the workflow and run `gitleaks git --log-level error --no-banner --redact --exit-code 1 --log-opts='--all' .`. Keep complete git history (`git fetch --unshallow` if applicable). Never print raw finding content.

Python requirements are not fully pinned: pip-audit resolves currently available packages at each run, **not** the deployed environment. Adopt locked dependencies to make Python results reproducible. `pip-audit`'s JSON does not consistently provide severity, so **all** Python advisories fail; npm fails high/critical, including development dependencies. npm scans use committed lockfiles and do not run `npm install` or alter manifests. The vulnerable `python-jose`/`ecdsa` stack and Zhipu SDK's `PyJWT<2.9` constraint were removed in favor of `PyJWT==2.14.0` and a fixed-origin OpenAI-compatible Zhipu transport; both Python audits passed locally after the migration.

## Time-limited exceptions

The registry `.github/security-audit-exceptions.json` is deliberately empty. Prefer upgrading dependencies. A temporary exception needs a security reviewer and a PR that adds an **individual advisory** object (never an entire package or severity bypass):

```json
{"ecosystem":"npm","package":"example-package","id":"GHSA-xxxx-xxxx-xxxx","expires":"2026-10-01","owner":"named-team","reason":"Specific impact analysis and compensating control","tracking_url":"https://example.com/tracked-remediation"}
```

Python accepts `CVE-YYYY-NNNN`, `PYSEC-YYYY-NNNN` or GHSA identifiers; npm uses the advisory GHSA identifier from its audit URL. Exceptions must be owned, have an HTTPS remediation tracker, and expire within 30 days of the CI run; CI rejects expired and overly long exceptions. An exception must be renewed by a reviewed PR with a new impact analysis, not automatically extended. A transitive high npm finding without a direct advisory cannot be bypassed by registry entry.

## Baseline requiring remediation or review

On 2026-09-26, the initial audit reported **13 high, 1 critical** for `apps/web-console` and **1 high** for `services/digital-brain/apps/web-console`. The dependencies and both lockfiles were then upgraded, including Next.js 16.3.6 and sharp 0.35.4, with `npm audit fix --package-lock-only` to refresh transitive dependencies. The repository npm gate subsequently passed locally with zero high/critical findings and no exceptions. Validate typecheck, navigation/API tests and production build on the upgraded stack. Python audit passed locally under Python 3.11 after normalizing a legacy non-UTF-8 requirements comment; CI must still verify it. Full-history Gitleaks v8.24.3 requires `--log-level error` instead of unsupported `--quiet`. With this fixed, the unfiltered local redacted full-history scan found six historical generic-api-key candidates. The repository owner confirmed in this H-11 review that the historical DashScope API key was revoked/rotated at the provider; its original value is deliberately not repeated or verified by this repository. `.gitleaksignore` records **only those six exact historical commit:file:rule:line fingerprints**, never a path/rule-level bypass: one revoked old provider key, four instances of the removed public `geo-rpa-secret-2026` worker default, and one test-only CRM idempotency identifier. Current API, worker, browser configuration and examples no longer contain the public worker default, and RPA endpoints reject empty/missing keys. Since the revoked key remains in immutable pre-PR Git history, an exact fingerprint exception avoids force-rewriting shared history; cloning an old commit still exposes that **revoked** value. New secrets and additional matches, even in the same file or rule, must fail. Review every new candidate privately; do not put raw findings or secrets in CI logs, tickets or PR comments. If provider revocation is uncertain, do not merge.
