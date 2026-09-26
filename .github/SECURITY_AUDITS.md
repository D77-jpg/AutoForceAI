# H-11 security audit gate

`.github/workflows/security-audit.yml` checks both Python requirements files with pinned `pip-audit`, both tracked npm lockfiles with `npm audit --package-lock-only`, and all Git history with pinned gitleaks. It runs on main/security-hardening pushes, PRs into main, manual dispatch, and weekly. Network or malformed scanner responses fail closed. Gitleaks uses redacted quiet output; do not paste findings or tokens into issues or logs. Rotate/revoke any actual exposed credentials and remove them from history using a coordinated response.

## Reproduce

On Python 3.11 and Node 20, at repository root:

```sh
python -m pip install 'pip-audit==2.10.1'
python .github/scripts/security_audit.py python services/digital-brain/requirements.txt services/rpa-worker/requirements.txt
python .github/scripts/security_audit.py npm apps/web-console services/digital-brain/apps/web-console
```

For full history secret scanning on Linux, install the pinned gitleaks release used by the workflow and run `gitleaks git --quiet --redact --exit-code 1 --log-opts='--all' .`. Keep complete git history (`git fetch --unshallow` if applicable). Never print raw finding content.

Python requirements are not fully pinned: pip-audit resolves currently available packages at each run, **not** the deployed environment. Adopt locked dependencies to make Python results reproducible. `pip-audit`'s JSON does not consistently provide severity, so **all** Python advisories fail; npm fails high/critical, including development dependencies. npm scans use committed lockfiles and do not run `npm install` or alter manifests.

## Time-limited exceptions

The registry `.github/security-audit-exceptions.json` is deliberately empty. Prefer upgrading dependencies. A temporary exception needs a security reviewer and a PR that adds an **individual advisory** object (never an entire package or severity bypass):

```json
{"ecosystem":"npm","package":"example-package","id":"GHSA-xxxx-xxxx-xxxx","expires":"2026-10-01","owner":"named-team","reason":"Specific impact analysis and compensating control","tracking_url":"https://example.com/tracked-remediation"}
```

Python accepts `CVE-YYYY-NNNN`, `PYSEC-YYYY-NNNN` or GHSA identifiers; npm uses the advisory GHSA identifier from its audit URL. Exceptions must be owned, have an HTTPS remediation tracker, and expire within 30 days of the CI run; CI rejects expired and overly long exceptions. An exception must be renewed by a reviewed PR with a new impact analysis, not automatically extended. A transitive high npm finding without a direct advisory cannot be bypassed by registry entry.

## Baseline requiring remediation or review

On 2026-09-26, `npm audit --package-lock-only --json` reported **13 high, 1 critical** for `apps/web-console`, and **1 high** for `services/digital-brain/apps/web-console`. Primary lockfile high/critical packages: axios, brace-expansion, browserslist, flatted, form-data, js-yaml, lodash, lodash-es, minimatch, nanoid, **next (critical)**, picomatch, postcss, sharp. Secondary lockfile: lodash-es (high; GHSA-r5fr-rjxr-66jc and GHSA-f23m-r3pf-42rh). The Next.js and sharp audit fixes require semver-major changes (`next` 16.3.6; `sharp` 0.35.4 according to the audit response). Upgrade and regression-test with application owners. This is a failing gate intentionally; **no blanket exceptions have been granted**. Current Python and history-scan baselines still require CI execution or equivalent local check.
