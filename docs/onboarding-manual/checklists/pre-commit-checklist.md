# Pre-Commit Checklist

**Purpose**: Comprehensive checklist to ensure code quality, security, and compatibility before committing changes to SomaBrain.

**Audience**: All developers contributing to SomaBrain codebase.

**Prerequisites**: Development environment setup per [Environment Setup](../environment-setup.md) and understanding of [Coding Standards](../../development-manual/coding-standards.md).

---

## Code Quality Checks

### [ ] Static Analysis
- [ ] **Linting**: Run `ruff check somabrain/ tests/` with zero violations
- [ ] **Type Checking**: Run `mypy somabrain/` with no type errors
- [ ] **Format Check**: Run `black --check somabrain/ tests/` - code is properly formatted
- [ ] **Import Sorting**: Run `isort --check-only somabrain/ tests/` - imports are sorted correctly
- [ ] **Security Scan**: Run `bandit -r somabrain/` with no high-severity issues

```bash
# Quick quality check script
#!/bin/bash
echo "Running pre-commit quality checks..."

# Linting
echo "→ Checking linting..."
ruff check somabrain/ tests/ || exit 1

# Type checking  
echo "→ Checking types..."
mypy somabrain/ || exit 1

# Formatting
echo "→ Checking formatting..."
black --check somabrain/ tests/ || exit 1

# Import sorting
echo "→ Checking import sorting..."
isort --check-only somabrain/ tests/ || exit 1

# Security scan
echo "→ Running security scan..."
bandit -r somabrain/ -f json -o bandit-report.json
bandit -r somabrain/ || exit 1

echo "✓ All quality checks passed!"
```

### [ ] Documentation
- [ ] **Docstrings**: All new functions/classes have complete docstrings following NumPy format
- [ ] **Type Hints**: All function parameters and return values have type annotations
- [ ] **Comments**: Complex logic has explanatory comments
- [ ] **API Documentation**: Changes to public APIs are documented in relevant manual sections

```python
# Example: Proper function documentation
async def store_memory(
    content: str,
    tenant_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    ttl_seconds: Optional[int] = None
) -> MemoryRecord:
    """Store a memory with vector encoding and metadata.
    
    Parameters
    ----------
    content : str
        The textual content to store as a memory.
    tenant_id : str
        Unique identifier for the tenant namespace.
    metadata : dict[str, Any], optional
        Additional key-value metadata to associate with the memory.
    ttl_seconds : int, optional
        Time-to-live in seconds. If provided, memory will expire automatically.
        
    Returns
    -------
    MemoryRecord
        The stored memory record with generated ID and vector encoding.
        
    Raises
    ------
    ValidationError
        If content is empty or tenant_id is invalid.
    EncodingError
        If vector encoding fails for the provided content.
    StorageError  
        If database storage operation fails.
        
    Examples
    --------
    >>> memory = await store_memory(
    ...     content="Python is a programming language",
    ...     tenant_id="user_123", 
    ...     metadata={"source": "user_input", "category": "programming"}
    ... )
    >>> print(memory.id)
    'mem_abc123'
    """
    # Implementation...
```

### [ ] Code Structure
- [ ] **Module Organization**: New code follows established package structure
- [ ] **Separation of Concerns**: Business logic separated from infrastructure code
- [ ] **Single Responsibility**: Functions/classes have single, clear responsibility
- [ ] **No Code Duplication**: Common functionality is extracted to shared utilities

---

## Testing Requirements

### [ ] Test Coverage
- [ ] **Unit Tests**: All new functions have corresponding unit tests
- [ ] **Integration Tests**: API changes include integration test coverage  
- [ ] **Coverage Threshold**: Overall test coverage remains above 85%
- [ ] **Edge Cases**: Tests cover error conditions and boundary cases

```bash
# Run tests with coverage
pytest --cov=somabrain --cov-report=html --cov-report=term-missing
# Check coverage threshold
coverage report --fail-under=85
```

### [ ] Test Quality  
- [ ] **Test Isolation**: Tests do not depend on external state or other tests
- [ ] **Descriptive Names**: Test function names clearly describe what is being tested
- [ ] **Arrange-Act-Assert**: Tests follow clear AAA pattern
- [ ] **Mock External Dependencies**: Network calls, file system, and databases are mocked appropriately

```python
# Example: Well-structured test
@pytest.mark.asyncio
async def test_store_memory_creates_vector_encoding():
    """Test that storing a memory generates appropriate vector encoding."""
    # Arrange
    content = "Test memory content for encoding"
    tenant_id = "test_tenant_123"
    mock_encoder = Mock()
    mock_encoder.encode.return_value = np.array([0.1, 0.2, 0.3])
    
    # Act
    with patch('somabrain.core.memory_manager.vector_encoder', mock_encoder):
        memory = await memory_manager.store_memory(content, tenant_id)
    
    # Assert
    assert memory.vector_encoding is not None
    assert len(memory.vector_encoding) == 3
    mock_encoder.encode.assert_called_once_with(content)
```

### [ ] Test Execution
- [ ] **All Tests Pass**: Run `pytest tests/` - all tests pass locally
- [ ] **Fast Test Suite**: Unit tests complete in under 30 seconds
- [ ] **No Test Warnings**: No deprecation warnings or test collection issues
- [ ] **Database Tests**: Integration tests use test database, not production data

---

## Security Verification

### [ ] Secrets and Credentials
- [ ] **No Hardcoded Secrets**: API keys, passwords, tokens are not in source code
- [ ] **Environment Variables**: Sensitive configuration uses environment variables
- [ ] **Test Data**: No production data or real credentials in test files
- [ ] **.env.example Updated**: New environment variables documented in example file

```bash
# Check for potential secrets in code
git diff HEAD^ --name-only | xargs grep -E "(password|secret|key|token)" || echo "No secrets found"

# Verify no .env file is tracked
git ls-files | grep -E "\.env$" && echo "ERROR: .env file is tracked!" || echo "OK"
```

### [ ] Input Validation
- [ ] **Parameter Validation**: All user inputs are validated before processing
- [ ] **SQL Injection Prevention**: Database queries use parameterized statements
- [ ] **XSS Prevention**: User content is properly escaped in responses
- [ ] **File Upload Safety**: File uploads validate type, size, and content

```python
# Example: Proper input validation
from pydantic import BaseModel, validator

class MemoryRequest(BaseModel):
    content: str
    tenant_id: str
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        if len(v) > 10000:  # 10KB limit
            raise ValueError('Content exceeds maximum length')
        return v.strip()
    
    @validator('tenant_id')
    def valid_tenant_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid tenant ID format')
        return v
```

### [ ] Dependencies
- [ ] **Vulnerability Scan**: Run `safety check` - no known vulnerabilities
- [ ] **License Compliance**: New dependencies have compatible licenses
- [ ] **Minimal Dependencies**: Only necessary dependencies are added
- [ ] **Version Pinning**: Dependencies are pinned to specific versions

---

## Performance Considerations

### [ ] Resource Usage
- [ ] **Memory Usage**: Changes do not significantly increase memory consumption
- [ ] **Database Queries**: No N+1 query problems introduced
- [ ] **Async Operations**: I/O operations use async/await appropriately  
- [ ] **Caching**: Expensive operations are cached when appropriate

```python
# Check for potential performance issues
async def check_performance_impact():
    # Memory usage before
    import psutil
    process = psutil.Process()
    mem_before = process.memory_info().rss
    
    # Run your code change
    result = await your_new_function()
    
    # Memory usage after
    mem_after = process.memory_info().rss
    mem_increase = (mem_after - mem_before) / 1024 / 1024  # MB
    
    assert mem_increase < 100, f"Memory increase too high: {mem_increase}MB"
```

### [ ] Scalability
- [ ] **Batch Processing**: Large data sets are processed in batches
- [ ] **Connection Management**: Database connections are properly managed
- [ ] **Rate Limiting**: API endpoints handle rate limiting gracefully
- [ ] **Concurrent Safety**: Shared resources are properly protected

---

## Compatibility Checks

### [ ] API Compatibility
- [ ] **Backward Compatibility**: Public API changes are backward compatible
- [ ] **Version Requirements**: Changes work with specified Python/dependency versions
- [ ] **Environment Support**: Code works in development, staging, and production environments
- [ ] **Database Migration**: Schema changes include proper migration scripts

### [ ] Integration Testing
- [ ] **Docker Build**: `docker build -t somabrain .` completes successfully
- [ ] **Docker Compose**: `docker-compose up` starts all services correctly
- [ ] **API Endpoints**: All modified endpoints return expected responses
- [ ] **Client SDKs**: Changes work with existing client library versions

```bash
# Integration test script
#!/bin/bash
echo "Running integration tests..."

# Build Docker image
echo "→ Building Docker image..."
docker build -t somabrain:test . || exit 1

# Start services
echo "→ Starting services..."
docker-compose -f docker-compose.test.yml up -d || exit 1

# Wait for services to be ready
echo "→ Waiting for services..."
sleep 30

# Test API endpoints
echo "→ Testing API endpoints..."
curl -f http://localhost:9696/health || exit 1
curl -f http://localhost:9696/metrics || exit 1

# Run integration tests
echo "→ Running integration tests..."
pytest tests/integration/ || exit 1

# Cleanup
echo "→ Cleaning up..."
docker-compose -f docker-compose.test.yml down

echo "✓ All integration tests passed!"
```

---

## Documentation Updates

### [ ] Code Documentation
- [ ] **README Updates**: Changes are reflected in README.md if applicable
- [ ] **API Documentation**: OpenAPI/Swagger documentation is updated
- [ ] **Configuration Guide**: New configuration options are documented
- [ ] **Migration Guide**: Breaking changes include migration instructions

### [ ] Manual Updates
- [ ] **User Manual**: User-facing changes documented in [User Manual](../../user-manual/)
- [ ] **Technical Manual**: Operational changes documented in [Technical Manual](../../technical-manual/)
- [ ] **Development Manual**: Development process changes documented in [Development Manual](../../development-manual/)
- [ ] **Cross-References**: Documentation links are updated and valid

---

## Git Best Practices

### [ ] Commit Quality
- [ ] **Commit Message**: Clear, descriptive commit message following conventional format
- [ ] **Single Purpose**: Commit contains related changes for single feature/fix
- [ ] **File Organization**: Only relevant files are included in commit
- [ ] **No Debug Code**: Temporary debug statements, console.log, print statements removed

```
# Good commit message format:
feat(memory): add vector similarity threshold configuration

Add configurable similarity threshold for memory search operations.
This allows tenants to control precision vs recall tradeoffs.

- Add VECTOR_SIMILARITY_THRESHOLD environment variable
- Update search logic to use configurable threshold  
- Add validation for threshold range (0.0-1.0)
- Update documentation and tests

Closes #123
```

### [ ] Branch Status
- [ ] **Up to Date**: Branch is rebased on latest main/develop branch
- [ ] **Clean History**: No merge commits or unnecessary commits in branch  
- [ ] **Conflict Resolution**: All merge conflicts resolved properly
- [ ] **Feature Complete**: All work for the feature/fix is included

```bash
# Pre-commit git checks
git status                    # No unexpected changes
git diff --staged            # Review staged changes
git log --oneline -10        # Check recent commits
git diff main..HEAD --stat   # See what changes vs main
```

---

## Final Verification

### [ ] End-to-End Testing
- [ ] **Manual Testing**: Critical user flows tested manually
- [ ] **Error Handling**: Error cases produce appropriate responses
- [ ] **Logging**: Important operations are logged appropriately  
- [ ] **Monitoring**: Relevant metrics are captured

### [ ] Team Communication
- [ ] **PR Description**: Pull request has clear description of changes
- [ ] **Breaking Changes**: Breaking changes are highlighted and documented
- [ ] **Review Requirements**: Appropriate reviewers are assigned
- [ ] **Dependencies**: Dependent changes in other repositories are coordinated

**Verification**: Pre-commit checklist is complete when all items are checked and verified.

---

**Common Errors**:

| Error | Solution |
|-------|----------|
| Tests fail locally | Run `pytest tests/ -v` to identify specific failures |
| Linting violations | Run `ruff check --fix` and `black somabrain/` |
| Type errors | Add missing type hints and fix type mismatches |
| Import errors | Run `isort somabrain/ tests/` to fix import order |
| Security issues | Review `bandit` output and fix flagged issues |

**References**:
- [Coding Standards](../../development-manual/coding-standards.md) for detailed style guidelines
- [Testing Guidelines](../../development-manual/testing-guidelines.md) for testing best practices
- [Contribution Process](../../development-manual/contribution-process.md) for PR workflow
- [Setup Checklist](setup-checklist.md) for environment verification