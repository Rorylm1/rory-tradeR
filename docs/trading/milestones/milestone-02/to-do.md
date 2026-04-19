# Milestone 02 To-Do

## Objective

Create a secure and documented workflow for acquiring, validating, and inspecting upstream historical data before it is used locally.

## Checklist

- [x] Inspect the upstream setup scripts and document the exact data download path.
- [x] Record the upstream archive URL, expected size, and expected extraction layout.
- [ ] Define the quarantine-first extraction workflow in docs.
- [ ] Implement a checksum verification workflow and record expected SHA-256 values once available.
- [x] Add a `data-verify` CLI command or equivalent validation entrypoint.
- [x] Add tests for checksum validation and archive structure checks.
- [x] Ensure the workflow fails closed on unexpected paths or malformed archives.
- [ ] Ensure the workflow does not auto-delete the original archive before validation completes.

## Exit Criteria

- [ ] No one needs to run `make setup` blindly.
- [ ] Historical data can be acquired with a repeatable verification path.
- [ ] The repo clearly separates trusted code from untrusted bulk data.
