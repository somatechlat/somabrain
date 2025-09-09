Commit guidelines
=================

This project uses a lightweight Conventional Commits style together with pre-commit hooks to keep the repo clean and consistent.

Quick rules
- Use a short, imperative subject line: `type(scope): short description`
  - Types: feat, fix, docs, style, refactor, perf, test, chore, ci
  - Scope is optional, e.g. `api`, `quantum`, `docs`.
- Add a longer body when you need to explain why the change is necessary.
- Reference issues in the footer: `Fixes #123`.

Setup (one-time for developers)
1. Install pre-commit: `pip install pre-commit` or use your environment manager.
2. From the repo root run:

```bash
scripts/setup_precommit.sh
```

This will install the git hooks and configure the local commit template.

Pre-commit hooks
- Formatters: black, isort
- Linters: ruff (auto-fix enabled)
- Repo hygiene: end-of-file-fixer, trailing-whitespace, check-yaml

If a hook fails, fix the issues and re-run `git add` on the changed files. Hooks run automatically on `git commit`.

Commit message template
- The repository contains a commit message template in `.gitmessage`. Set it locally with:

```bash
git config commit.template .gitmessage
```

CI / Release notes
- The project CI runs unit tests and doc build on PRs. Follow the test and lint results before merging.

Thank you for keeping the project clean and easy to maintain.
