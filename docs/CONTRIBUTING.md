# Contribution Process

**Purpose**: Complete workflow guide for contributing code, documentation, and improvements to SomaBrain, including development practices and review processes.

**Audience**: Contributors, maintainers, and open source developers working on SomaBrain project.

**Prerequisites**: Understanding of [Local Setup](local-setup.md), [Coding Standards](coding-standards.md), and [Testing Guidelines](testing-guidelines.md).

---

## Contribution Overview

### Contribution Types

**Bug Fixes**: Resolve existing issues and improve stability
**Feature Development**: Add new functionality and capabilities
**Documentation**: Improve guides, API docs, and code comments
**Performance**: Optimize algorithms, database queries, and system performance
**Refactoring**: Improve code structure without changing functionality
**Security**: Address vulnerabilities and improve security posture

### Project Governance

**Core Maintainers**: Review and approve changes, set project direction
**Contributors**: Submit pull requests, participate in discussions
**Community**: Report issues, suggest features, provide feedback

---

## Getting Started

### Fork and Clone

1. **Fork the Repository**:
   ```bash
   # Navigate to https://github.com/somabrain/somabrain
   # Click "Fork" button to create your fork
   ```

2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/somabrain.git
   cd somabrain

   # Add upstream remote
   git remote add upstream https://github.com/somabrain/somabrain.git

   # Verify remotes
   git remote -v
   ```

3. **Set Up Development Environment**:
   ```bash
   # Follow local setup guide
   make setup

   # Verify installation
   make test
   make lint
   ```

### Issue Selection

**Good First Issues**: Look for `good-first-issue` label for newcomers
**Bug Reports**: Check `bug` label for confirmed issues
**Feature Requests**: Review `enhancement` label for approved features
**Documentation**: Find `documentation` label for doc improvements

**Issue Assignment**: Comment on issue to request assignment before starting work

---

## Development Workflow

### Branch Strategy

**Main Branch**: `main` - Production-ready code
**Development Branch**: `develop` - Integration branch for features
**Feature Branches**: `feature/issue-number-short-description`
**Bugfix Branches**: `bugfix/issue-number-short-description`
**Hotfix Branches**: `hotfix/issue-number-short-description`

### Creating Feature Branch

```bash
# Update your fork
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/123-add-memory-search
```

### Development Process

1. **Understand the Requirements**:
   - Read issue description completely
   - Ask questions in issue comments
   - Review related code and documentation
   - Understand acceptance criteria

2. **Plan the Implementation**:
   ```python
   # Example: Planning memory search feature

   # 1. Define API endpoint structure
   # POST /memories/search
   # {
   #   "query": "search terms",
   #   "filters": {"category": "technical"},
   #   "options": {"k": 10, "threshold": 0.3}
   # }

   # 2. Identify components to modify
   # - Add search endpoint to FastAPI router
   # - Implement search logic in MemoryManager
   # - Add database search method
   # - Create response models
   # - Add comprehensive tests

   # 3. Consider edge cases
   # - Empty query handling
   # - Invalid filter handling
   # - Performance with large datasets
   # - Tenant isolation
   ```

3. **Implement Changes**:
   ```python
   # somabrain/api/routers/memory.py
   from fastapi import APIRouter, Depends, HTTPException
   from typing import List, Optional

   from somabrain.models.search import SearchRequest, SearchResponse
   from somabrain.core.memory_manager import MemoryManager
   from somabrain.api.dependencies import get_memory_manager, get_current_tenant

   router = APIRouter()

   @router.post("/search", response_model=SearchResponse)
   async def search_memories(
       request: SearchRequest,
       memory_manager: MemoryManager = Depends(get_memory_manager),
       tenant_id: str = Depends(get_current_tenant)
   ):
       """
       Search memories using semantic similarity.

       Args:
           request: Search parameters including query and filters
           memory_manager: Injected memory manager instance
           tenant_id: Current tenant identifier

       Returns:
           SearchResponse with matching memories and metadata

       Raises:
           HTTPException: For invalid requests or search failures
       """
       try:
           # Validate request
           if not request.query.strip():
               raise HTTPException(
                   status_code=400,
                   detail="Search query cannot be empty"
               )

           # Perform search
           results = await memory_manager.search_memories(
               query=request.query,
               filters=request.filters,
               k=request.options.k,
               threshold=request.options.threshold,
               tenant_id=tenant_id
           )

           return SearchResponse(
               results=results,
               total_count=len(results),
               query=request.query,
               processing_time_ms=results.processing_time
           )

       except ValueError as e:
           raise HTTPException(status_code=400, detail=str(e))
       except Exception as e:
           logger.error(f"Search failed: {e}", exc_info=True)
           raise HTTPException(
               status_code=500,
               detail="Search operation failed"
           )
   ```

4. **Write Comprehensive Tests**:
   ```python
   # tests/unit/api/test_memory_search.py
   import pytest
   from fastapi.testclient import TestClient
   from unittest.mock import AsyncMock, patch

   from somabrain.api.main import app
   from somabrain.models.memory import Memory

   client = TestClient(app)

   @pytest.fixture
   def mock_search_results():
       """Mock search results for testing."""
       return [
           Memory(
               id="mem_1",
               content="Test content 1",
               similarity_score=0.9,
               metadata={"category": "test"}
           ),
           Memory(
               id="mem_2",
               content="Test content 2",
               similarity_score=0.8,
               metadata={"category": "test"}
           )
       ]

   @patch('somabrain.api.routers.memory.get_memory_manager')
   def test_search_memories_success(mock_get_manager, mock_search_results):
       """Test successful memory search."""
       # Arrange
       mock_manager = AsyncMock()
       mock_manager.search_memories.return_value = mock_search_results
       mock_get_manager.return_value = mock_manager

       # Act
       response = client.post(
           "/memories/search",
           json={
               "query": "test query",
               "filters": {"category": "test"},
               "options": {"k": 10, "threshold": 0.3}
           },
           headers={"X-Tenant-ID": "test-tenant", "X-API-Key": "test-key"}
       )

       # Assert
       assert response.status_code == 200
       data = response.json()
       assert len(data["results"]) == 2
       assert data["query"] == "test query"
       assert data["total_count"] == 2

   def test_search_empty_query():
       """Test search with empty query fails validation."""
       response = client.post(
           "/memories/search",
           json={
               "query": "",
               "options": {"k": 10}
           },
           headers={"X-Tenant-ID": "test-tenant", "X-API-Key": "test-key"}
       )

       assert response.status_code == 400
       assert "empty" in response.json()["detail"].lower()

   def test_search_invalid_parameters():
       """Test search with invalid parameters."""
       response = client.post(
           "/memories/search",
           json={
               "query": "test",
               "options": {"k": -1}  # Invalid k value
           },
           headers={"X-Tenant-ID": "test-tenant", "X-API-Key": "test-key"}
       )

       assert response.status_code == 400
   ```

5. **Update Documentation**:
   ```markdown
   # Update API documentation
   # docs/development/api-reference.md

   ### Search Memories

   Search for memories using semantic similarity.

   **Endpoint**: `POST /memories/search`

   **Request**:
   ```json
   {
     "query": "search terms here",
     "filters": {"category": "technical"},
     "options": {"k": 10, "threshold": 0.3}
   }
   ```
   ```

### Code Quality Checks

**Pre-commit Checks**:
```bash
# Run all quality checks before committing
make lint          # Code linting and formatting
make type-check    # Type checking with mypy
make test          # Run test suite
make security      # Security vulnerability scan
```

**Automated Quality Gates**:
```bash
# Setup pre-commit hooks (one-time)
pre-commit install

# Pre-commit will automatically run:
# - black (code formatting)
# - isort (import sorting)
# - flake8 (linting)
# - mypy (type checking)
# - pytest (unit tests)
# - safety (security checks)
```

### Commit Guidelines

**Commit Message Format**:
```
type(scope): Brief description of changes

More detailed explanation if needed. Explain what changed,
why it changed, and any important details.

Closes #issue_number
```

**Commit Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example Commits**:
```bash
# Feature commit
git commit -m "feat(api): add memory search endpoint

Implement semantic search for memories with filtering support.
Includes comprehensive tests and API documentation.

Closes #123"

# Bug fix commit
git commit -m "fix(auth): handle expired JWT tokens correctly

Previously expired tokens would cause server errors.
Now returns proper 401 Unauthorized response.

Fixes #456"

# Documentation commit
git commit -m "docs(api): update memory search examples

Add Python and JavaScript SDK examples for new search endpoint.
Include error handling patterns and best practices.

Closes #789"
```

---

## Pull Request Process

### Creating Pull Request

1. **Push Your Branch**:
   ```bash
   git push origin feature/123-add-memory-search
   ```

2. **Open Pull Request**:
   - Navigate to your fork on GitHub
   - Click "Compare & pull request"
   - Select base repository: `somabrain/somabrain`
   - Select base branch: `develop`
   - Select compare branch: your feature branch

3. **Fill PR Template**:
   ```markdown
   ## Description
   Brief description of changes and motivation.

   ## Type of Change
   - [ ] Bug fix (non-breaking change that fixes an issue)
   - [x] New feature (non-breaking change that adds functionality)
   - [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
   - [ ] Documentation update

   ## Testing
   - [x] Unit tests pass
   - [x] Integration tests pass
   - [x] Manual testing completed
   - [ ] Performance testing (if applicable)

   ## Checklist
   - [x] Code follows style guidelines
   - [x] Self-review completed
   - [x] Code is commented where needed
   - [x] Documentation updated
   - [x] Tests added/updated
   - [x] No breaking changes (or clearly documented)

   ## Related Issues
   Closes #123

   ## Screenshots (if applicable)
   Add screenshots for UI changes.
   ```

### PR Review Process

**Review Stages**:

1. **Automated Checks** (Required to pass):
   - ✅ Code formatting (black, isort)
   - ✅ Linting (flake8, pylint)
   - ✅ Type checking (mypy)
   - ✅ Unit tests (pytest)
   - ✅ Integration tests
   - ✅ Security scan (safety, bandit)
   - ✅ Code coverage (>80% for new code)

2. **Code Review** (At least 2 approvals required):
   - **Architecture Review**: Design patterns, system integration
   - **Code Quality**: Readability, maintainability, performance
   - **Security Review**: Vulnerability assessment, best practices
   - **Testing Review**: Test coverage, edge cases, integration

3. **Documentation Review**:
   - API documentation accuracy
   - Code comments and docstrings
   - User-facing documentation updates
   - Changelog entries

### Addressing Review Feedback

**Responding to Comments**:
```bash
# Make requested changes
git add .
git commit -m "fix: address review feedback

- Add input validation for edge cases
- Improve error message clarity
- Add missing docstrings
- Fix type hints"

git push origin feature/123-add-memory-search
```

**Resolving Conflicts**:
```bash
# Update your branch with latest develop
git checkout develop
git pull upstream develop
git checkout feature/123-add-memory-search
git rebase develop

# Resolve any conflicts in your editor
# Then continue rebase
git add .
git rebase --continue

# Force push updated branch
git push origin feature/123-add-memory-search --force-with-lease
```

### PR Merge Process

**Merge Requirements**:
- ✅ All automated checks pass
- ✅ At least 2 code review approvals
- ✅ No unresolved review comments
- ✅ Up-to-date with target branch
- ✅ Changelog updated (for user-facing changes)

**Merge Methods**:
- **Squash and Merge**: For feature branches (preferred)
- **Merge Commit**: For complex changes requiring history
- **Rebase and Merge**: For small, clean commits

---

## Testing Requirements

### Test Coverage

**Minimum Coverage**: 80% for new code, 90% for critical components

**Required Tests**:
```python
# Unit tests for all new functions/methods
def test_memory_search_with_filters():
    """Test memory search with metadata filters."""
    pass

def test_memory_search_empty_query():
    """Test memory search handles empty query."""
    pass

def test_memory_search_invalid_filters():
    """Test memory search with invalid filter format."""
    pass

# Integration tests for API endpoints
async def test_search_api_integration():
    """Test complete search API workflow."""
    pass

# Performance tests for critical paths
def test_search_performance_large_dataset():
    """Test search performance with large memory dataset."""
    pass
```

### Test Categories

**Unit Tests** (Required for all changes):
- Function/method behavior
- Edge cases and error conditions
- Input validation
- Algorithm correctness

**Integration Tests** (Required for API/DB changes):
- API endpoint functionality
- Database operations
- Service interactions
- Authentication/authorization

**End-to-End Tests** (Required for user-facing features):
- Complete user workflows
- Cross-component integration
- Real-world scenarios
- Performance under load

---

## Release Process

### Version Management

**Semantic Versioning**: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Version Examples**:
- `1.0.0` → `1.0.1`: Bug fix release
- `1.0.1` → `1.1.0`: New feature release
- `1.1.0` → `2.0.0`: Breaking changes

### Release Preparation

```bash
# 1. Create release branch
git checkout develop
git pull upstream develop
git checkout -b release/v1.1.0

# 2. Update version numbers
# - pyproject.toml
# - package.json (if applicable)
# - version.py

# 3. Update changelog
# Add release notes to CHANGELOG.md

# 4. Run full test suite
make test-all
make benchmark

# 5. Build and test packages
make build
make test-package

# 6. Create release PR to main
```

### Release Workflow

1. **Feature Freeze**: Stop merging new features
2. **Release Candidate**: Deploy to staging environment
3. **Testing Phase**: Comprehensive testing and validation
4. **Release Notes**: Document all changes and breaking changes
5. **Release Deployment**: Merge to main and deploy
6. **Post-Release**: Merge back to develop, create tags

---

## Documentation Standards

### Code Documentation

**Python Docstrings** (Google Style):
```python
def search_memories(
    self,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    k: int = 10,
    threshold: float = 0.2
) -> List[Memory]:
    """
    Search for memories using semantic similarity.

    Performs vector similarity search on stored memories, applying
    optional metadata filters to narrow results.

    Args:
        query: Search query text for semantic matching
        filters: Optional metadata filters as key-value pairs
        k: Maximum number of results to return (1-100)
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        List of Memory objects sorted by similarity score descending.

    Raises:
        ValueError: If query is empty or parameters are invalid
        SearchError: If search operation fails

    Example:
        >>> manager = MemoryManager()
        >>> results = manager.search_memories(
        ...     query="Python programming",
        ...     filters={"category": "technical"},
        ...     k=5
        ... )
        >>> print(f"Found {len(results)} memories")
    """
```

**API Documentation**:
- OpenAPI/Swagger specifications
- Request/response examples
- Error code documentation
- SDK usage examples

**Architecture Documentation**:
- System design decisions
- Component interactions
- Data flow diagrams
- Performance characteristics

### Changelog Maintenance

**Format**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2024-01-15

### Added
- Memory search API endpoint with filtering support
- WebSocket real-time notifications
- Batch memory operations

### Changed
- Improved vector similarity performance by 30%
- Updated API authentication to use JWT tokens

### Deprecated
- Legacy authentication endpoints (will be removed in v2.0)

### Fixed
- Memory update race condition in concurrent operations
- Tenant isolation bug in search results

### Security
- Fixed potential SQL injection in metadata filters
- Added rate limiting to prevent abuse
```

---

## Community Guidelines

### Communication Channels

**GitHub Issues**: Bug reports, feature requests, discussions
**GitHub Discussions**: General questions, ideas, community chat
**Slack/Discord**: Real-time chat with maintainers and contributors
**Email**: Security issues and private matters

### Code of Conduct

**Our Pledge**: Foster an open, welcoming, and inclusive community

**Expected Behavior**:
- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

**Unacceptable Behavior**:
- Harassment, discrimination, or intimidation
- Trolling, insulting comments, or personal attacks
- Publishing private information without permission
- Any conduct inappropriate in a professional setting

### Issue Reporting

**Bug Report Template**:
```markdown
**Bug Description**
Clear description of the bug.

**Steps to Reproduce**
1. Go to...
2. Click on...
3. See error...

**Expected Behavior**
What should have happened.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Python version: [e.g. 3.11]
- SomaBrain version: [e.g. 1.0.1]

**Additional Context**
Screenshots, logs, or other relevant information.
```

**Feature Request Template**:
```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
Clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Screenshots, mockups, or other relevant information.
```

---

## Performance Guidelines

### Performance Requirements

**Response Time Targets**:
- Memory storage: < 200ms (p95)
- Memory search: < 500ms (p95)
- Memory retrieval: < 100ms (p95)
- Batch operations: < 2000ms (p95)

**Throughput Targets**:
- Memory storage: > 100 requests/second
- Search queries: > 200 requests/second
- Concurrent users: > 1000

### Performance Testing

**Load Testing**:
```python
# Use locust for load testing
from locust import HttpUser, task, between

class SomaBrainLoadTest(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {
            "X-API-Key": "test-key",
            "X-Tenant-ID": "load-test-tenant"
        }

    @task(3)
    def search_memories(self):
        self.client.post("/recall", json={
            "query": "test search query",
            "k": 10
        }, headers=self.headers)

    @task(1)
    def store_memory(self):
        self.client.post("/remember", json={
            "content": "Load test memory content",
            "metadata": {"source": "load_test"}
        }, headers=self.headers)
```

**Benchmarking**:
```bash
# Run performance benchmarks
make benchmark

# Specific benchmarks
pytest tests/performance/ -v --benchmark-only
```

**Verification**: Contribution process is effective when code quality is high, review cycles are efficient, and community participation is active.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Pre-commit hooks fail | Run `make lint` and fix formatting issues |
| Tests fail in CI | Ensure all tests pass locally first |
| Review takes too long | Address feedback promptly and completely |
| Merge conflicts | Keep branch updated with develop regularly |
| Coverage drops | Add tests for all new code paths |

**References**:
- [Local Setup Guide](local-setup.md) for development environment
- [Coding Standards](coding-standards.md) for code quality requirements
- [Testing Guidelines](testing-guidelines.md) for comprehensive testing
- [API Reference](api-reference.md) for API development patterns