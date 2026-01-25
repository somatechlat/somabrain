# Documentation Style Guide

This style guide follows the **ISO/IEC/IEEE 12207** standard for software documentation.

## General Principles

* **Clarity** – Use simple language, avoid jargon where possible.
* **Consistency** – Follow the same heading hierarchy, terminology, and formatting throughout.
* **Traceability** – Every requirement, design decision, and test case should be traceable to a source (e.g., ISO clause, user story).
* **Accessibility** – Content must comply with WCAG 2.1 AA.

## Document Structure

All documentation lives under the `docs/` directory and uses the following top-level sections:

1. **User Manual** (`docs/user/`) – Guides for end-users and operators.
2. **Technical Manual** (`docs/technical/`) – Architecture, deployment, and internal design.
3. **Development Manual** (`docs/development/`) – Setup, contribution workflow, and coding standards.
4. **Onboarding Manual** (`docs/onboarding/`) – Introductory material for new team members.
5. **Reference Materials** (`docs/reference/`) – Glossary, style guide, security classification.
6. **SRS Documents** (`docs/srs/`) – Software Requirements Specifications.

Each section contains an `index.md` that links to its subsections.

## Formatting Conventions

* **Headings** – Use ATX style (`#`, `##`, `###`). Top-level (`#`) is reserved for file titles.
* **Code blocks** – Use fenced code blocks with language identifier:
  ```python
  def foo():
      pass
  ```
* **Tables** – Markdown tables for enumerations, classification, and traceability.
* **Diagrams** – PlantUML (`*.puml`) or Mermaid (`*.mmd`) files placed alongside the markdown that references them.
* **Metadata** – Every markdown file starts with a YAML front-matter block (`---`) containing `title`, `author`, `date`, and `tags`.

## Test Documentation

* **Test Scope** – Tests are divided into:
  - `tests/aaas/` – Multi-tenant AAAS tests
  - `tests/standalone/` – Single-tenant standalone tests
  - `tests/integration/` – Infrastructure integration tests
  - `tests/unit/` – Unit tests
* **No Skipping** – Tests MUST fail (not skip) when infrastructure is unavailable.
* **Real Infrastructure** – All tests run against real services, no mocks.

## Review Process

All documentation changes must be recorded in `review-log.md` and undergo at least one peer review before merging to `master`.

---
*Based on somafractalmemory documentation standards.*
