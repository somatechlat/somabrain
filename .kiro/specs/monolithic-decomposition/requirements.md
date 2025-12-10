# Requirements Document

## Introduction

This specification defines the requirements for decomposing monolithic files in the SomaBrain codebase. The goal is to reduce file sizes to under 500 lines while maintaining functionality, improving maintainability, and following VIBE Coding Rules. The primary targets are `somabrain/app.py` (4052 lines), `somabrain/memory_client.py` (2216 lines), and `somabrain/metrics_original.py` (1698 lines).

## Glossary

- **Monolithic File**: A single source file containing multiple unrelated concerns exceeding 500 lines
- **Module Extraction**: The process of moving cohesive code units to separate files
- **Backward Compatibility**: Maintaining existing import paths and API signatures
- **DI Container**: Dependency Injection container for managing singletons (`somabrain/core/container.py`)
- **Router**: FastAPI APIRouter for grouping related endpoints
- **Settings**: Centralized configuration from `common/config/settings`

## Requirements

### Requirement 1

**User Story:** As a developer, I want `somabrain/app.py` decomposed into focused modules, so that I can understand and modify specific functionality without navigating a 4000+ line file.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the `somabrain/app.py` file SHALL contain fewer than 800 lines
2. WHEN endpoint handlers are extracted THEN the system SHALL maintain all existing API routes and response formats
3. WHEN helper functions are extracted THEN the system SHALL preserve all function signatures and return types
4. WHEN classes are extracted THEN the system SHALL maintain backward-compatible imports via `__init__.py` re-exports
5. WHEN startup/shutdown logic is extracted THEN the system SHALL preserve the application lifecycle behavior

### Requirement 2

**User Story:** As a developer, I want `somabrain/memory_client.py` decomposed into transport, normalization, and client modules, so that each concern is isolated and testable.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the `somabrain/memory_client.py` file SHALL contain fewer than 500 lines
2. WHEN the HTTP transport is extracted THEN the system SHALL maintain all connection pooling and retry behavior
3. WHEN normalization functions are extracted THEN the system SHALL preserve vector normalization semantics
4. WHEN the client class is refactored THEN the system SHALL maintain the existing `MemoryClient` API

### Requirement 3

**User Story:** As a developer, I want `somabrain/metrics_original.py` reorganized into logical metric groups, so that related metrics are co-located and discoverable.

#### Acceptance Criteria

1. WHEN the decomposition is complete THEN the `somabrain/metrics_original.py` file SHALL contain fewer than 500 lines
2. WHEN metrics are grouped THEN the system SHALL organize them by domain (learning, memory, outbox, health)
3. WHEN metric functions are extracted THEN the system SHALL maintain all existing metric names and labels
4. WHEN the metrics module is restructured THEN the system SHALL preserve backward-compatible imports via `somabrain/metrics/__init__.py`

### Requirement 4

**User Story:** As a developer, I want all extracted modules to follow consistent patterns, so that the codebase remains coherent and predictable.

#### Acceptance Criteria

1. WHEN modules are extracted THEN the system SHALL use lazy imports to avoid circular dependencies
2. WHEN singletons are needed THEN the system SHALL use the DI container pattern from `somabrain/core/container.py`
3. WHEN configuration is needed THEN the system SHALL use centralized Settings from `common/config/settings`
4. WHEN errors occur THEN the system SHALL use structured logging with appropriate log levels

### Requirement 5

**User Story:** As a developer, I want the decomposition to be incremental and safe, so that each step can be validated before proceeding.

#### Acceptance Criteria

1. WHEN a module is extracted THEN the system SHALL pass all existing unit tests
2. WHEN a module is extracted THEN the system SHALL pass all existing property tests
3. WHEN imports are reorganized THEN the system SHALL maintain backward compatibility for at least one release cycle
4. WHEN the decomposition is complete THEN the system SHALL have no circular import errors

### Requirement 6

**User Story:** As a developer, I want secondary large files (500-1000 lines) addressed, so that the entire codebase follows the 500-line guideline.

#### Acceptance Criteria

1. WHEN `somabrain/api/memory_api.py` (1615 lines) is refactored THEN the file SHALL contain fewer than 500 lines
2. WHEN `somabrain/learning/adaptation.py` (1071 lines) is refactored THEN the file SHALL contain fewer than 500 lines
3. WHEN `somabrain/schemas.py` (1003 lines) is refactored THEN the file SHALL contain fewer than 500 lines
4. WHEN `somabrain/routers/memory.py` (720 lines) is refactored THEN the file SHALL contain fewer than 500 lines
