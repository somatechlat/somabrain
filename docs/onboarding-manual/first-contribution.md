# First Contribution

**Purpose**: Complete walkthrough for making your first code contribution to SomaBrain, from issue selection to pull request merge.

**Audience**: New contributors, developers making their first SomaBrain contribution, and team members learning the workflow.

**Prerequisites**: Completed [Environment Setup](environment-setup.md) and read [Codebase Walkthrough](codebase-walkthrough.md).

---

## Overview

This guide will walk you through contributing a small but meaningful feature to SomaBrain. We'll implement a simple memory search filter that demonstrates the complete development workflow.

**Feature Goal**: Add a memory age filter to the recall API (e.g., "only show memories from the last 7 days")

**Learning Objectives**:
- Navigate the contribution process
- Understand code quality requirements
- Practice testing patterns
- Experience the review process

---

## Step 1: Issue Selection and Planning

### Find Your First Issue

**Good First Issues**:
1. Visit [GitHub Issues](https://github.com/somabrain/somabrain/issues)
2. Look for `good-first-issue` label
3. Read issue description completely
4. Check if anyone is already assigned

**Example Issue**: "Add date range filtering to memory recall API"

**Issue Analysis**:
```markdown
# Issue #456: Add date range filtering to memory recall API

## Description
Users want to filter recalled memories by creation date (e.g., "memories from last week").

## Acceptance Criteria
- [ ] Add `date_range` parameter to recall API
- [ ] Support relative filters (e.g., "7d", "1month")  
- [ ] Support absolute date ranges
- [ ] Add comprehensive tests
- [ ] Update API documentation

## Technical Notes
- Modify `/recall` endpoint in `somabrain/api/routers/memory.py`
- Add date filtering to database query
- Ensure tenant isolation is maintained
```

### Claim the Issue

**Comment on Issue**:
```markdown
Hi! I'd like to work on this issue. I'm new to the project and this looks like a good learning opportunity.

My plan:
1. Add `date_range` parameter to RecallRequest model
2. Implement date parsing and validation
3. Add database filtering logic
4. Write comprehensive tests
5. Update API documentation

I'll have a PR ready within 3-4 days. Let me know if this approach sounds good!
```

**Wait for Assignment**: Maintainers will assign the issue and provide guidance.

---

## Step 2: Development Setup

### Create Feature Branch

```bash
# Ensure you're on develop branch
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/456-date-range-filtering

# Verify branch
git branch
```

### Understand Current Implementation

**Examine Current Code**:
```bash
# Look at current recall endpoint
cat somabrain/api/routers/memory.py

# Check request/response models
cat somabrain/models/memory.py

# Review database query logic
cat somabrain/database/operations.py
```

**Study the Pattern**:
```python
# Current recall endpoint structure
@router.post("/recall", response_model=RecallResponse)
async def recall_memories(
    request: RecallRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    tenant_id: str = Depends(get_current_tenant)
):
    # 1. Validate request
    # 2. Convert query to vector
    # 3. Search database with filters
    # 4. Return results
```

---

## Step 3: Implementation

### 1. Update Data Models

**Extend RecallRequest Model** (`somabrain/models/memory.py`):
```python
from datetime import datetime, date
from typing import Optional, Union, Literal
from pydantic import BaseModel, validator

class DateRange(BaseModel):
    """Date range filter for memory recall."""
    
    # Relative ranges (e.g., "7d", "1w", "1month")
    relative: Optional[str] = None
    
    # Absolute ranges  
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('relative')
    def validate_relative_format(cls, v):
        """Validate relative date format."""
        if v is None:
            return v
            
        import re
        pattern = r'^(\d+)(d|w|month|year)$'
        if not re.match(pattern, v.lower()):
            raise ValueError(
                'Relative date must be format like "7d", "2w", "1month", "1year"'
            )
        return v.lower()
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date."""
        if v is not None and values.get('start_date') is not None:
            if v <= values['start_date']:
                raise ValueError('end_date must be after start_date')
        return v

class RecallRequest(BaseModel):
    """Request model for memory recall API."""
    
    query: str
    k: int = 10
    threshold: float = 0.2
    filters: Optional[Dict[str, Any]] = {}
    
    # New date range filtering
    date_range: Optional[DateRange] = None
    
    include_metadata: bool = True
    include_scores: bool = True

    @validator('k')
    def validate_k(cls, v):
        if not 1 <= v <= 100:
            raise ValueError('k must be between 1 and 100')
        return v
        
    @validator('threshold')
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('threshold must be between 0.0 and 1.0')
        return v
```

### 2. Add Date Range Utility Functions

**Create Date Utilities** (`somabrain/utils/date_helpers.py`):
```python
from datetime import datetime, timedelta
from typing import Tuple
import re

def parse_relative_date(relative_str: str) -> Tuple[datetime, datetime]:
    """
    Parse relative date string to absolute date range.
    
    Args:
        relative_str: String like "7d", "2w", "1month", "1year"
        
    Returns:
        Tuple of (start_datetime, end_datetime)
        
    Raises:
        ValueError: If format is invalid
    """
    pattern = r'^(\d+)(d|w|month|year)$'
    match = re.match(pattern, relative_str.lower())
    
    if not match:
        raise ValueError(f"Invalid relative date format: {relative_str}")
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    end_date = datetime.utcnow()
    
    if unit == 'd':
        start_date = end_date - timedelta(days=amount)
    elif unit == 'w':
        start_date = end_date - timedelta(weeks=amount)
    elif unit == 'month':
        # Approximate month as 30 days
        start_date = end_date - timedelta(days=amount * 30)
    elif unit == 'year':
        # Approximate year as 365 days
        start_date = end_date - timedelta(days=amount * 365)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")
    
    return start_date, end_date

def get_date_range_filter(date_range: DateRange) -> Tuple[datetime, datetime]:
    """
    Convert DateRange model to absolute datetime range.
    
    Args:
        date_range: DateRange model with relative or absolute dates
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    if date_range.relative:
        return parse_relative_date(date_range.relative)
    
    elif date_range.start_date or date_range.end_date:
        start_date = date_range.start_date or datetime.min
        end_date = date_range.end_date or datetime.utcnow()
        return start_date, end_date
    
    else:
        raise ValueError("DateRange must specify either relative or absolute dates")
```

### 3. Update Database Layer

**Extend Database Query** (`somabrain/database/operations.py`):
```python
async def search_memories_with_filters(
    self,
    query_vector: np.ndarray,
    tenant_id: str,
    limit: int = 10,
    threshold: float = 0.2,
    metadata_filters: Optional[Dict[str, Any]] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None
) -> List[Memory]:
    """
    Search memories with comprehensive filtering.
    
    Args:
        query_vector: Vector representation of search query
        tenant_id: Tenant isolation identifier
        limit: Maximum results to return
        threshold: Minimum similarity threshold
        metadata_filters: JSON metadata filters
        date_range: Optional (start_date, end_date) tuple
        
    Returns:
        List of matching Memory objects with similarity scores
    """
    
    # Base query with vector similarity
    query = """
    SELECT 
        id, content, metadata, created_at, updated_at,
        1 - (vector_encoding <=> $1) AS similarity_score
    FROM memories 
    WHERE 
        tenant_id = $2
        AND (1 - (vector_encoding <=> $1)) >= $3
    """
    
    params = [query_vector.tolist(), tenant_id, threshold]
    param_count = 3
    
    # Add metadata filtering if provided
    if metadata_filters:
        param_count += 1
        query += f" AND metadata @> ${param_count}"
        params.append(json.dumps(metadata_filters))
    
    # Add date range filtering if provided
    if date_range:
        start_date, end_date = date_range
        param_count += 1
        query += f" AND created_at >= ${param_count}"
        params.append(start_date)
        
        param_count += 1
        query += f" AND created_at <= ${param_count}"
        params.append(end_date)
    
    # Order by similarity and limit results
    query += f"""
    ORDER BY vector_encoding <=> $1
    LIMIT ${param_count + 1}
    """
    params.append(limit)
    
    # Execute query
    async with self.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    
    # Convert to Memory objects
    memories = []
    for row in rows:
        memory = Memory(
            id=row['id'],
            content=row['content'],
            metadata=row['metadata'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            similarity_score=row['similarity_score'],
            tenant_id=tenant_id
        )
        memories.append(memory)
    
    return memories
```

### 4. Update API Endpoint

**Modify Recall Endpoint** (`somabrain/api/routers/memory.py`):
```python
@router.post("/recall", response_model=RecallResponse)
async def recall_memories(
    request: RecallRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Recall semantically similar memories with optional filtering.
    
    Enhanced with date range filtering to find memories within
    specific time periods.
    """
    try:
        # Validate request
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="Search query cannot be empty"
            )
        
        # Parse date range if provided
        date_range_filter = None
        if request.date_range:
            try:
                from somabrain.utils.date_helpers import get_date_range_filter
                date_range_filter = get_date_range_filter(request.date_range)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date range: {str(e)}"
                )
        
        # Perform memory search with all filters
        results = await memory_manager.recall_memories_with_filters(
            query=request.query,
            k=request.k,
            threshold=request.threshold,
            metadata_filters=request.filters,
            date_range=date_range_filter,
            tenant_id=tenant_id
        )
        
        return RecallResponse(
            results=results,
            total_results=len(results),
            query=request.query,
            processing_time_ms=results.processing_time if hasattr(results, 'processing_time') else 0
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Memory recall failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Memory recall operation failed"
        )
```

---

## Step 4: Testing

### 1. Write Unit Tests

**Test Date Utilities** (`tests/unit/utils/test_date_helpers.py`):
```python
import pytest
from datetime import datetime, timedelta
from somabrain.utils.date_helpers import parse_relative_date, get_date_range_filter
from somabrain.models.memory import DateRange

class TestDateHelpers:
    """Unit tests for date utility functions."""

    def test_parse_relative_date_days(self):
        """Test parsing relative dates in days."""
        start_date, end_date = parse_relative_date("7d")
        
        # Should be approximately 7 days ago to now
        expected_start = datetime.utcnow() - timedelta(days=7)
        expected_end = datetime.utcnow()
        
        # Allow 1 minute tolerance for test execution time
        assert abs((start_date - expected_start).total_seconds()) < 60
        assert abs((end_date - expected_end).total_seconds()) < 60

    def test_parse_relative_date_weeks(self):
        """Test parsing relative dates in weeks.""" 
        start_date, end_date = parse_relative_date("2w")
        
        expected_start = datetime.utcnow() - timedelta(weeks=2)
        assert abs((start_date - expected_start).total_seconds()) < 60

    def test_parse_relative_date_months(self):
        """Test parsing relative dates in months."""
        start_date, end_date = parse_relative_date("1month")
        
        expected_start = datetime.utcnow() - timedelta(days=30)
        assert abs((start_date - expected_start).total_seconds()) < 60

    def test_parse_relative_date_invalid_format(self):
        """Test error handling for invalid formats."""
        with pytest.raises(ValueError, match="Invalid relative date format"):
            parse_relative_date("invalid")
        
        with pytest.raises(ValueError, match="Invalid relative date format"):
            parse_relative_date("7x")  # Invalid unit

    def test_get_date_range_filter_relative(self):
        """Test DateRange with relative dates."""
        date_range = DateRange(relative="7d")
        start_date, end_date = get_date_range_filter(date_range)
        
        expected_start = datetime.utcnow() - timedelta(days=7)
        assert abs((start_date - expected_start).total_seconds()) < 60

    def test_get_date_range_filter_absolute(self):
        """Test DateRange with absolute dates."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        
        date_range = DateRange(start_date=start, end_date=end)
        start_date, end_date = get_date_range_filter(date_range)
        
        assert start_date == start
        assert end_date == end

    def test_date_range_validation_invalid_range(self):
        """Test validation of invalid date ranges."""
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            DateRange(
                start_date=datetime(2024, 1, 31),
                end_date=datetime(2024, 1, 1)  # Before start_date
            )

    def test_date_range_validation_relative_format(self):
        """Test validation of relative date formats."""
        # Valid formats
        DateRange(relative="7d")
        DateRange(relative="2w") 
        DateRange(relative="1month")
        DateRange(relative="1year")
        
        # Invalid formats
        with pytest.raises(ValueError):
            DateRange(relative="invalid")
        
        with pytest.raises(ValueError):
            DateRange(relative="7x")
```

**Test API Endpoint** (`tests/unit/api/test_memory_recall.py`):
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from somabrain.api.main import app
from somabrain.models.memory import Memory

client = TestClient(app)

class TestRecallWithDateRange:
    """Test memory recall API with date range filtering."""

    @patch('somabrain.api.routers.memory.get_memory_manager')
    def test_recall_with_relative_date_range(self, mock_get_manager):
        """Test recall with relative date range filter."""
        
        # Mock memory manager
        mock_manager = AsyncMock()
        mock_manager.recall_memories_with_filters.return_value = [
            Memory(
                id="mem_1",
                content="Recent memory",
                similarity_score=0.9,
                created_at=datetime.utcnow() - timedelta(days=2)
            )
        ]
        mock_get_manager.return_value = mock_manager
        
        # Make API request
        response = client.post(
            "/recall",
            json={
                "query": "test query",
                "k": 10,
                "date_range": {
                    "relative": "7d"
                }
            },
            headers={"X-Tenant-ID": "test-tenant", "X-API-Key": "test-key"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == "Recent memory"
        
        # Verify manager was called with date filter
        mock_manager.recall_memories_with_filters.assert_called_once()
        call_kwargs = mock_manager.recall_memories_with_filters.call_args.kwargs
        assert call_kwargs["date_range"] is not None

    @patch('somabrain.api.routers.memory.get_memory_manager')
    def test_recall_with_absolute_date_range(self, mock_get_manager):
        """Test recall with absolute date range filter."""
        
        mock_manager = AsyncMock()
        mock_manager.recall_memories_with_filters.return_value = []
        mock_get_manager.return_value = mock_manager
        
        response = client.post(
            "/recall",
            json={
                "query": "test query",
                "date_range": {
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-01-31T23:59:59"
                }
            },
            headers={"X-Tenant-ID": "test-tenant", "X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        
    def test_recall_invalid_date_range(self):
        """Test recall with invalid date range returns 400."""
        
        response = client.post(
            "/recall", 
            json={
                "query": "test query",
                "date_range": {
                    "relative": "invalid_format"
                }
            },
            headers={"X-Tenant-ID": "test-tenant", "X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        assert "Invalid date range" in response.json()["detail"]
```

### 2. Write Integration Tests

**Database Integration Test** (`tests/integration/test_date_filtering.py`):
```python
import pytest
from datetime import datetime, timedelta
import asyncio

from somabrain.database.connection import DatabaseManager
from somabrain.models.memory import Memory

@pytest.mark.integration
class TestDateRangeFiltering:
    """Integration tests for date range filtering."""

    @pytest.fixture
    async def populated_database(self, database_manager):
        """Create test memories with different creation dates."""
        
        # Create memories from different time periods
        memories = [
            # Recent memories (last 3 days)
            ("Recent memory 1", datetime.utcnow() - timedelta(days=1)),
            ("Recent memory 2", datetime.utcnow() - timedelta(days=2)),
            
            # Older memories (last week)  
            ("Week old memory", datetime.utcnow() - timedelta(days=6)),
            
            # Much older memories (last month)
            ("Month old memory", datetime.utcnow() - timedelta(days=25)),
        ]
        
        memory_ids = []
        for content, created_at in memories:
            # Manually set created_at (normally would be auto-generated)
            memory_id = await database_manager.store_memory_with_timestamp(
                content=content,
                metadata={"category": "integration_test"},
                vector_encoding=np.random.rand(384).astype(np.float32),
                tenant_id="test_tenant",
                created_at=created_at
            )
            memory_ids.append(memory_id)
        
        return memory_ids

    @pytest.mark.asyncio
    async def test_date_range_filtering_recent_only(
        self, 
        database_manager, 
        populated_database
    ):
        """Test filtering to show only recent memories."""
        
        # Search for memories from last 3 days
        date_range = (
            datetime.utcnow() - timedelta(days=3),
            datetime.utcnow()
        )
        
        results = await database_manager.search_memories_with_filters(
            query_vector=np.random.rand(384).astype(np.float32),
            tenant_id="test_tenant",
            limit=10,
            threshold=0.0,  # Very low threshold to get all results
            date_range=date_range
        )
        
        # Should only return recent memories
        assert len(results) == 2  # Only the 2 recent memories
        
        recent_contents = [r.content for r in results]
        assert "Recent memory 1" in recent_contents
        assert "Recent memory 2" in recent_contents
        assert "Week old memory" not in recent_contents
        assert "Month old memory" not in recent_contents

    @pytest.mark.asyncio
    async def test_date_range_filtering_week_range(
        self, 
        database_manager, 
        populated_database
    ):
        """Test filtering for memories from last week."""
        
        date_range = (
            datetime.utcnow() - timedelta(days=7),
            datetime.utcnow()
        )
        
        results = await database_manager.search_memories_with_filters(
            query_vector=np.random.rand(384).astype(np.float32),
            tenant_id="test_tenant",
            limit=10,
            threshold=0.0,
            date_range=date_range
        )
        
        # Should return recent + week old memories (3 total)
        assert len(results) == 3
        
        contents = [r.content for r in results]
        assert "Week old memory" in contents
        assert "Month old memory" not in contents
```

### 3. Run All Tests

```bash
# Run new unit tests
pytest tests/unit/utils/test_date_helpers.py -v
pytest tests/unit/api/test_memory_recall.py -v

# Run integration tests
pytest tests/integration/test_date_filtering.py -v

# Run full test suite to ensure no regressions
pytest tests/ -v

# Check test coverage
pytest tests/ --cov=somabrain --cov-report=html
open htmlcov/index.html
```

---

## Step 5: Documentation

### Update API Documentation

**Add Examples to API Reference** (`docs/development-manual/api-reference.md`):
```markdown
### Recall Memories with Date Filtering

**Enhanced Request Example**:
```json
{
  "query": "Python web framework performance",
  "k": 10,
  "threshold": 0.3,
  "filters": {
    "category": "technical"
  },
  "date_range": {
    "relative": "7d"
  }
}
```

**Date Range Options**:

**Relative Dates**:
```json
{
  "date_range": {
    "relative": "7d"     // Last 7 days
  }
}

{
  "date_range": {
    "relative": "2w"     // Last 2 weeks  
  }
}

{
  "date_range": {
    "relative": "1month" // Last month (approx 30 days)
  }
}
```

**Absolute Dates**:
```json
{
  "date_range": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  }
}
```
```

### Update User Manual

**Add to Memory Operations Guide** (`docs/user-manual/memory-operations.md`):
```markdown
### Filtering by Date Range

You can limit search results to specific time periods:

**Recent Memories Only**:
```python
# Find memories from last week
results = await client.recall(
    query="project requirements",
    date_range={"relative": "1w"}
)
```

**Specific Date Range**:
```python
# Find memories from January 2024
results = await client.recall(
    query="quarterly planning",
    date_range={
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-01-31T23:59:59Z" 
    }
)
```

**Supported Relative Formats**:
- `7d` - Last 7 days
- `2w` - Last 2 weeks  
- `1month` - Last month (30 days)
- `1year` - Last year (365 days)
```

---

## Step 6: Code Quality

### Run Quality Checks

```bash
# Format code
black somabrain/ tests/
isort somabrain/ tests/

# Check linting
flake8 somabrain/ tests/

# Type checking
mypy somabrain/

# Run pre-commit hooks
pre-commit run --all-files
```

### Fix Any Issues

**Example Linting Fixes**:
```bash
# If flake8 reports line too long:
# Split long lines at logical points

# Before (line too long):
query += f" AND created_at >= ${param_count} AND created_at <= ${param_count + 1}"

# After (properly split):
query += f" AND created_at >= ${param_count}"
param_count += 1
query += f" AND created_at <= ${param_count}"
```

**Type Checking Fixes**:
```python
# Add missing type hints
from typing import Optional, Tuple, List, Dict, Any

def parse_relative_date(relative_str: str) -> Tuple[datetime, datetime]:
    # Implementation...
    pass
```

---

## Step 7: Commit and Push

### Create Meaningful Commits

```bash
# Stage changes by logical groups
git add somabrain/models/memory.py
git commit -m "feat: add DateRange model for memory filtering

- Add DateRange model with relative and absolute date support
- Include validation for date formats and ranges
- Support relative formats like '7d', '2w', '1month'"

git add somabrain/utils/date_helpers.py
git commit -m "feat: add date parsing utilities

- Implement parse_relative_date for relative date strings
- Add get_date_range_filter for DateRange model conversion
- Include comprehensive error handling"

git add somabrain/database/operations.py
git commit -m "feat: extend database search with date filtering

- Add date_range parameter to search_memories_with_filters
- Implement efficient SQL date range queries
- Maintain tenant isolation and performance"

git add somabrain/api/routers/memory.py
git commit -m "feat: add date range filtering to recall API

- Extend RecallRequest with optional date_range parameter
- Add date range validation and error handling
- Maintain backward compatibility"

git add tests/
git commit -m "test: add comprehensive tests for date filtering

- Unit tests for date utilities and validation
- Integration tests for database date filtering
- API tests for recall endpoint with date ranges
- Achieve 100% code coverage for new features"

git add docs/
git commit -m "docs: update API and user documentation

- Add date range filtering examples to API reference
- Update user manual with usage patterns
- Include troubleshooting for common date format errors"
```

### Push Feature Branch

```bash
# Push to your fork
git push origin feature/456-date-range-filtering

# Verify push succeeded
git log --oneline -5
```

---

## Step 8: Create Pull Request

### Open PR on GitHub

1. **Navigate to Repository**: Go to your fork on GitHub
2. **Create PR**: Click "Compare & pull request" 
3. **Select Branches**: 
   - Base repository: `somabrain/somabrain`
   - Base branch: `develop`
   - Compare branch: `feature/456-date-range-filtering`

### Write PR Description

```markdown
# Add Date Range Filtering to Memory Recall API

Fixes #456

## Summary

This PR adds date range filtering capability to the `/recall` API endpoint, allowing users to search for memories within specific time periods.

## Changes Made

### New Features
- **DateRange Model**: Support for relative (`"7d"`, `"2w"`) and absolute date ranges
- **Date Utilities**: Parsing and validation functions for date ranges  
- **Database Filtering**: Extended search query with efficient date range filtering
- **API Enhancement**: Added optional `date_range` parameter to recall endpoint

### Technical Details
- Maintains backward compatibility - `date_range` parameter is optional
- Efficient SQL queries using indexed `created_at` column
- Comprehensive input validation with helpful error messages
- Full test coverage including unit and integration tests

## Testing

- ✅ Unit tests for all new functions (100% coverage)
- ✅ Integration tests with real database
- ✅ API tests for all scenarios (success, validation errors)
- ✅ Backward compatibility verified
- ✅ Performance tested with large datasets

## Documentation

- ✅ API reference updated with examples
- ✅ User manual includes usage patterns
- ✅ Inline code documentation added

## Breaking Changes

None - this is a backward-compatible enhancement.

## Examples

**Relative Date Filtering**:
```json
{
  "query": "project updates", 
  "date_range": {"relative": "7d"}
}
```

**Absolute Date Filtering**:
```json
{
  "query": "quarterly goals",
  "date_range": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-03-31T23:59:59Z"
  }
}
```

## Checklist

- [x] Code follows style guidelines
- [x] Self-review completed  
- [x] Tests added and passing
- [x] Documentation updated
- [x] No breaking changes
- [x] Performance impact considered
- [x] Security implications reviewed

## Notes for Reviewers

- The date parsing logic handles edge cases like leap years and month boundaries
- Database queries are optimized and use existing indexes
- Error messages are user-friendly and actionable
- Consider reviewing the SQL query optimization in `operations.py`
```

---

## Step 9: Address Review Feedback

### Typical Review Comments

**Example Review Feedback**:
```markdown
**@maintainer-alice commented:**

Great work on the implementation! A few suggestions:

1. **Performance**: The SQL query could use an index on (tenant_id, created_at) for better performance with large datasets.

2. **Error Handling**: Consider adding more specific error types for different validation failures.

3. **Documentation**: Could you add a note about timezone handling in the API docs?

4. **Testing**: Add an edge case test for leap year handling in the date utilities.

Overall looks good, just these minor improvements needed!
```

### Address Feedback

**1. Add Database Index**:
```bash
# Create new migration
alembic revision -m "add index for date filtering performance"

# Edit migration file
# migrations/versions/xxx_add_date_index.py
def upgrade():
    op.create_index(
        'ix_memories_tenant_created_performance', 
        'memories',
        ['tenant_id', 'created_at']
    )

def downgrade():
    op.drop_index('ix_memories_tenant_created_performance')
```

**2. Improve Error Handling**:
```python
# somabrain/exceptions.py
class DateRangeError(ValidationError):
    """Specific error for date range validation issues."""
    pass

# somabrain/utils/date_helpers.py  
def parse_relative_date(relative_str: str) -> Tuple[datetime, datetime]:
    try:
        # existing implementation...
    except ValueError as e:
        raise DateRangeError(f"Invalid date format '{relative_str}': {str(e)}")
```

**3. Add Timezone Documentation**:
```markdown
### Date Range Timezone Handling

All dates are processed in UTC timezone. When providing absolute dates:

- Include timezone information: `2024-01-01T00:00:00Z`
- Omitted timezone is assumed UTC
- Relative dates are calculated from current UTC time
```

**4. Add Leap Year Test**:
```python
def test_leap_year_handling(self):
    """Test date parsing handles leap years correctly.""" 
    # Test during leap year Feb 29
    with patch('somabrain.utils.date_helpers.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2024, 2, 29, 12, 0, 0)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        start_date, end_date = parse_relative_date("1year")
        
        # Should correctly handle leap year boundary
        expected_start = datetime(2023, 2, 28, 12, 0, 0)  # No leap day in 2023
        assert abs((start_date - expected_start).total_seconds()) < 86400  # Within 1 day
```

### Update PR

```bash
# Make requested changes
git add .
git commit -m "fix: address review feedback

- Add database index for (tenant_id, created_at) performance
- Improve error handling with specific DateRangeError
- Add timezone documentation to API reference  
- Add leap year test coverage"

git push origin feature/456-date-range-filtering
```

### Respond to Review

```markdown
Thanks @maintainer-alice for the thorough review! I've addressed all the feedback:

1. ✅ **Performance**: Added migration for (tenant_id, created_at) index
2. ✅ **Error Handling**: Created DateRangeError class with specific error messages
3. ✅ **Documentation**: Added timezone handling section to API docs
4. ✅ **Testing**: Added leap year edge case test

The updated PR should be ready for final review. Let me know if you need any other changes!
```

---

## Step 10: Merge and Celebration

### Final Approval

**Maintainer Response**:
```markdown
Perfect! All feedback addressed. The implementation looks solid:

- ✅ Clean, well-tested code
- ✅ Good performance considerations
- ✅ Excellent documentation
- ✅ Backward compatible

Approved for merge! 🎉

Welcome to the SomaBrain contributor community! This was an excellent first contribution.
```

### Post-Merge Cleanup

```bash
# Switch back to develop
git checkout develop

# Pull the merged changes
git pull upstream develop

# Delete feature branch (optional)
git branch -d feature/456-date-range-filtering
git push origin --delete feature/456-date-range-filtering

# Update your fork
git push origin develop
```

### Share Your Success

**Comment on Original Issue**:
```markdown
🎉 Feature implemented and merged! 

The date range filtering is now available in the `/recall` API. Users can filter memories using:

- Relative dates: `"7d"`, `"2w"`, `"1month"`, `"1year"`  
- Absolute dates: ISO format with timezone support

Documentation and examples are available in the updated API reference.

Thanks for the great first issue suggestion!
```

---

## Learning Outcomes

### Skills Developed

**Technical Skills**:
- ✅ FastAPI endpoint development
- ✅ Pydantic model design and validation
- ✅ SQL query optimization
- ✅ Async Python patterns
- ✅ Test-driven development
- ✅ Database migrations

**Process Skills**:
- ✅ Git workflow with feature branches
- ✅ Code review process
- ✅ Documentation writing
- ✅ Issue analysis and planning
- ✅ Community communication

**SomaBrain-Specific Knowledge**:
- ✅ API architecture patterns
- ✅ Database layer design
- ✅ Testing strategies
- ✅ Documentation standards
- ✅ Performance considerations

### Next Steps

**More Advanced Contributions**:
1. **Performance Optimization**: Work on query performance or caching
2. **New Features**: Implement more complex cognitive reasoning features
3. **Infrastructure**: Improve deployment, monitoring, or observability
4. **SDK Development**: Contribute to Python or TypeScript client libraries

**Mentorship Opportunities**:
- Help other new contributors with their first PRs
- Review documentation for clarity
- Participate in community discussions

**Verification**: First contribution is successful when PR is merged, tests pass, and feature works in production.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Tests fail after changes | Run tests locally before pushing |
| Merge conflicts | Keep feature branch updated with develop |
| Review feedback overwhelming | Address one comment at a time |
| Code style errors | Use pre-commit hooks and run linting |
| Documentation unclear | Get feedback from team members |

**References**:
- [Codebase Walkthrough](codebase-walkthrough.md) for understanding architecture
- [Environment Setup](environment-setup.md) for development environment
- [Development Manual](../development-manual/contribution-process.md) for detailed process
- [PR Checklist](checklists/pr-checklist.md) before submitting pull requests