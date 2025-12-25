# First Contribution

Purpose: Help new contributors ship their first PR successfully.

Audience: New engineers and external contributors.

Prerequisites:
- Local setup complete (see local-setup.md)
- Repo cloned and tests runnable

Steps:
1. Pick a good-first-issue or small doc fix.
2. Create a feature branch: `git checkout -b feat/short-description`.
3. Run quality gates locally:
   - `ruff check .`
   - `mypy somabrain`
   - `pytest -q`
4. Implement the change with tests.
5. Update docs if behavior changed.
6. Commit using conventional commits: `feat: ...`, `fix: ...`, `docs: ...`.
7. Push and open a PR. Fill the PR template, link issues.
8. Ensure CI passes and request review from codeowners.

Definition of Done:
- CI green (lint, typecheck, tests)
- Reviewer approvals
- Changelog entry added if user-visible

References:
- coding-standards.md
- testing-guidelines.md
- contribution-process.md
