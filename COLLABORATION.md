# Collaboration and Contribution Guidelines

Goal: make contributions easy and reviewable.

- Use feature branches named `feature/<short>` or `fix/<short>` or `harden/<area>`.
- Run tests locally before opening PRs: `./scripts/repo_prepare.sh` will install dev deps, run tests, run benchmark, and build docs.
- Keep changes minimal and focused in each PR. Add tests for new behavior.
- For numerical or behavioral contract changes (for example, normalization fallback), add a short design note and tests that demonstrate intended behavior.
