# Security Guide

## Security Objective

This repository is trading-adjacent and handles external archives plus exchange credentials. It should default to safe, reviewable, fail-closed behavior.

## Trust Tiers

### Tier 1: Repo-tracked source code

- source: Git-tracked code and docs
- controls: review, tests, and explicit documentation

### Tier 2: Package dependencies

- source: PyPI and locked dependencies in `uv.lock`
- controls: pinned versions, lockfile review, minimal dependency growth

### Tier 3: External bulk data

- source: historical datasets and downloaded archives
- controls: checksum, provenance recording, quarantine extraction, manual confirmation

## Historical Data Workflow

Do not run upstream `make setup` blindly.

Required workflow:
1. inspect upstream setup scripts
2. record source URL and expected size
3. download archive
4. compute SHA-256
5. inspect archive contents before extraction
6. extract in quarantine first
7. move validated data into local working directories only after inspection

## Extraction Checklist

- top-level paths match expectation
- no suspicious executable content
- no path traversal entries
- no silent auto-delete of the source archive before validation

## Secret Handling

- use `.env` for secrets only
- never commit secrets
- never print raw tokens, passwords, or session identifiers
- scrub recorded fixtures before they are committed

## Paper-Only Rule

Milestone one is paper-only.

That means:
- no live order submission
- no unattended strategy loops
- no hidden execution path behind config defaults

## Promotion Checklist For Any Future Live Mode

- explicit live readiness review completed
- exchange constraints confirmed
- secret redaction tested
- kill switches tested
- operator confirmations documented
- clear go / no-go recorded in docs
