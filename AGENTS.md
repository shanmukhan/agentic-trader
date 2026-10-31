# Repository working instructions

## Documentation is part of every change

The user explicitly requires this for every future implementation task:

- Update `docs/how-to-use.md` and the relevant detailed usage guide whenever a
  feature is added or an existing workflow changes. Document commands, inputs,
  expected results, failure/recovery behavior and material limitations.
- Update the corresponding component Markdown files, `docs/implementation-plan.md`
  and `docs/CHANGELOG.md` with the actual implemented behavior and validation.
- Include meaningful unit and functional tests for financial and workflow changes.
  Use exact monetary accounting and independently verify persisted state.
- Keep simulated evidence distinct from real-market, broker and device acceptance.
- Make UI changes easy to understand: explain state, financial values, stale or
  incomplete data, available actions and their outcomes in plain language. Preserve
  accessible labels, keyboard/touch use, readable responsive layouts and confirmation
  for consequential operator actions. Include corresponding UI checks and usage docs.

Do this as part of the same change without waiting for a separate reminder or
permission. This file records the user's standing instruction; it does not assert
that unfinished milestones or external acceptance checks are complete.

## Backend release versions

The user requires a version for backend deployments as well as UI releases. Bump
the application version in `pyproject.toml`, `src/trading_agent/__init__.py` and
`uv.lock` together. Deploy to a fresh versioned release directory, record the
version and source hashes in the deployment manifest, and verify the running
`/health` version after restart. Retain the previous release for rollback; do not
overwrite a running backend in place or restore financial databases automatically.
