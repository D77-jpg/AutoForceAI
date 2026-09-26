#!/usr/bin/env python3
"""Fail closed on dependency findings; only exact, unexpired registry entries can pass."""

import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".github/security-audit-exceptions.json"
ID_RE = re.compile(r"^(GHSA-[a-z0-9-]+|CVE-\d{4}-\d+|PYSEC-\d{4}-\d+)$")


def exceptions():
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Exception registry must be an array")
    approved = set()
    today = dt.datetime.now(dt.timezone.utc).date()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"ecosystem", "package", "id", "expires", "owner", "reason", "tracking_url"}:
            raise ValueError("Each exception needs exactly ecosystem, package, id, expires, owner, reason, tracking_url")
        ecosystem, package, identifier = entry["ecosystem"], entry["package"], entry["id"]
        if ecosystem not in ("npm", "python") or not isinstance(package, str) or not package or not isinstance(identifier, str) or not ID_RE.fullmatch(identifier):
            raise ValueError("Invalid exception ecosystem, package or advisory ID")
        if any(not isinstance(entry[k], str) or not entry[k].strip() for k in ("owner", "reason", "tracking_url")) or not entry["tracking_url"].startswith("https://"):
            raise ValueError("Exceptions require an owner, reason and HTTPS tracking URL")
        expiry = dt.date.fromisoformat(entry["expires"])
        if expiry < today or expiry > today + dt.timedelta(days=30):
            raise ValueError(f"Expired or >30-day exception: {ecosystem}/{package}/{identifier}")
        key = (ecosystem, package, identifier)
        if key in approved:
            raise ValueError(f"Duplicate exception: {key}")
        approved.add(key)
    return approved


def run(command, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8-sig", errors="replace", check=False)
    # Do not emit scanner raw stdout/stderr: dependency output can disclose URLs/credentials.
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Scanner failed with exit {result.returncode}: {command[0]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Scanner did not return valid JSON: {command[0]}") from exc
    if not isinstance(data, (list, dict)) or (isinstance(data, dict) and data.get("error")):
        raise RuntimeError(f"Scanner returned an error: {command[0]}")
    return data


def check_python(paths, approved):
    failed = False
    for path in paths:
        file = ROOT / path
        if not file.is_file():
            raise ValueError(f"Missing requirements: {path}")
        data = run([sys.executable, "-m", "pip_audit", "--format", "json", "-r", path])
        if not isinstance(data, dict) or not isinstance(data.get("dependencies"), list):
            raise ValueError("Unexpected pip-audit JSON schema")
        for dep in data["dependencies"]:
            name = dep["name"]
            for vuln in dep.get("vulns", []):
                identifier = vuln["id"]
                allowed = ("python", name, identifier) in approved
                # pip-audit's JSON does not supply consistent severity: fail on ALL findings.
                print(f"{path}: {name} {identifier}: {'EXCEPTION' if allowed else 'FAIL'}")
                failed |= not allowed
    return failed


def check_npm(paths, approved):
    failed = False
    for path in paths:
        directory = ROOT / path
        if not (directory / "package-lock.json").is_file():
            raise ValueError(f"Missing npm package-lock.json: {path}")
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm:
            raise RuntimeError("npm executable missing")
        data = run([npm, "audit", "--json", "--package-lock-only", "--audit-level=high"], directory)
        if not isinstance(data, dict) or not isinstance(data.get("vulnerabilities"), dict):
            raise ValueError("Unexpected npm audit JSON schema")
        for name, vuln in data["vulnerabilities"].items():
            if vuln["severity"] not in ("high", "critical"):
                continue
            advisories = [item for item in vuln["via"] if isinstance(item, dict)]
            if not advisories:
                print(f"{path}: {name}: FAIL (transitive high/critical finding without direct advisory)")
                failed = True
            for advisory in advisories:
                identifier = str(advisory.get("url", "")).rstrip("/").split("/")[-1]
                allowed = ("npm", name, identifier) in approved
                print(f"{path}: {name} {identifier}: {'EXCEPTION' if allowed else 'FAIL'}")
                failed |= not allowed
    return failed


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("python", "npm"):
        raise ValueError("Usage: security_audit.py python <requirements...> | npm <directories...>")
    approved = exceptions()
    failed = check_python(sys.argv[2:], approved) if sys.argv[1] == "python" else check_npm(sys.argv[2:], approved)
    if failed:
        print("Security audit failed: remediate findings or request exact, owned, <=30-day exceptions.")
        return 1
    print("Security audit passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print(f"Security audit setup error: {exc}", file=sys.stderr)
        sys.exit(2)
