# Coding Standards and Testing Strategy

This document outlines the coding standards, linting, formatting, and testing strategy for the SomaBrain project.

## Coding Standards

- **Python Version:** The project requires Python 3.10 or higher.
- **Style Guide:** We follow the PEP 8 style guide for Python code.
- **Docstrings:** All public modules, classes, and functions should have comprehensive docstrings that follow the conventions in PEP 257.

## Linting and Formatting

We use the following tools to ensure code quality and consistency:

- **Black:** For automated code formatting.
- **isort:** For sorting imports.
- **Ruff:** For linting and identifying potential issues.

The configuration for these tools can be found in the `pyproject.toml` file.

## Testing Strategy

The project includes a comprehensive test suite to ensure the correctness and stability of the codebase. The tests are organized into three categories:

- **Unit Tests (`tests/unit`):** These tests focus on individual components and functions in isolation.
- **Integration Tests (`tests/integration`):** These tests verify the interactions between different components of the system.
- **End-to-End Tests (`tests/e2e`):** These tests validate the entire system from the API endpoints to the backend services.

### Running Tests

To run the tests, first install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Then, run the tests using `pytest`:

```bash
python -m pytest
```

To run only the unit tests and skip the integration tests, you can use the following command:

```bash
python -m pytest -m "not integration"
```
