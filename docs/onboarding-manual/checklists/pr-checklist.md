# PR Checklist

**Purpose**: Comprehensive checklist for pull request preparation, review, and merge process to ensure code quality and team coordination.

**Audience**: All developers submitting pull requests and conducting code reviews for SomaBrain.

**Prerequisites**: Completed [Pre-Commit Checklist](pre-commit-checklist.md) and familiarity with [Contribution Process](../../development-manual/contribution-process.md).

---

## Pre-Submission Requirements

### [ ] Branch Preparation
- [ ] **Branch Name**: Follows naming convention `feature/issue-123-short-description` or `fix/issue-456-bug-name`
- [ ] **Base Branch**: Branched from correct base (usually `main` or `develop`)
- [ ] **Rebase**: Branch is rebased on latest target branch with clean history
- [ ] **Commits**: Related commits are squashed; commit messages follow conventional format
- [ ] **Size**: PR contains reasonable number of changes (< 500 lines preferred)

```bash
# Pre-submission branch check
git checkout main
git pull origin main
git checkout feature/memory-search-improvements
git rebase main

# Check commit history
git log --oneline main..HEAD

# Check PR size
git diff main --stat
```

### [ ] Code Quality Verification
- [ ] **Pre-commit Checklist**: All items in [Pre-Commit Checklist](pre-commit-checklist.md) completed
- [ ] **CI Pipeline**: All automated checks pass in CI/CD pipeline
- [ ] **No Merge Conflicts**: Branch can be cleanly merged into target branch
- [ ] **Dependencies**: New dependencies are approved and documented

---

## PR Description Requirements

### [ ] Title and Description
- [ ] **Clear Title**: PR title clearly describes the change in < 50 characters
- [ ] **Detailed Description**: Description explains what, why, and how of the changes
- [ ] **Issue Reference**: References related issues using `Closes #123` or `Fixes #456`
- [ ] **Breaking Changes**: Breaking changes are clearly marked and explained

```markdown
# Example PR Description Template:

## Summary
Brief description of what this PR accomplishes.

## Changes Made
- Bullet point list of specific changes
- Include both code and documentation updates
- Mention any configuration changes

## Testing
- Describe how changes were tested
- Include any new test cases added
- Mention manual testing performed

## Breaking Changes
- List any breaking changes (or state "None")
- Include migration instructions if applicable

## Screenshots/Examples
- Include relevant screenshots or code examples
- Show before/after behavior if applicable

## Checklist
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Ready for review

Closes #123
```

### [ ] Technical Documentation
- [ ] **Architecture Changes**: Significant architectural changes are documented
- [ ] **API Changes**: API modifications include examples and migration guide
- [ ] **Configuration**: New configuration options are documented with examples
- [ ] **Performance Impact**: Performance implications are described

---

## Review Requirements

### [ ] Reviewer Assignment
- [ ] **Code Owner Review**: Code owners for affected areas are assigned as reviewers
- [ ] **Domain Expert**: Subject matter expert is assigned for complex changes
- [ ] **Security Review**: Security-sensitive changes have security team review
- [ ] **Documentation Review**: Documentation changes have technical writer review

```yaml
# Example CODEOWNERS file entries
/somabrain/core/          @senior-dev @architect
/somabrain/api/           @api-team @security-team  
/somabrain/ml/            @ml-team @data-scientist
/docs/                    @tech-writers @docs-team
/infra/                   @devops-team @infrastructure
/security/                @security-team @cto
```

### [ ] Review Criteria
- [ ] **Code Quality**: Code follows established standards and patterns
- [ ] **Test Coverage**: Adequate test coverage for new functionality
- [ ] **Documentation**: Changes are properly documented
- [ ] **Security**: No security vulnerabilities introduced
- [ ] **Performance**: No significant performance degradation

---

## Self-Review Process

### [ ] Code Review
- [ ] **Review Own Changes**: Reviewed entire diff line by line
- [ ] **Remove Debug Code**: All debug prints, commented code, TODOs removed
- [ ] **Error Handling**: Appropriate error handling for all failure modes
- [ ] **Resource Cleanup**: Proper resource management (connections, files, etc.)

### [ ] Testing Verification
- [ ] **Local Testing**: All tests pass locally on clean environment
- [ ] **Integration Testing**: Changes tested with realistic data and scenarios
- [ ] **Edge Cases**: Boundary conditions and error cases tested
- [ ] **Backwards Compatibility**: Existing functionality still works

```python
# Self-review checklist for code changes
class MemorySearchImprover:
    """Improves memory search functionality with enhanced ranking."""
    
    def __init__(self, config: SearchConfig) -> None:
        # ✓ Type hints present
        # ✓ Docstring follows NumPy format
        # ✓ Proper error handling setup
        self.config = config
        self._validator = SearchValidator()
        
    async def search_memories(
        self, 
        query: str, 
        tenant_id: str,
        *,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[MemoryResult]:
        """Search for memories with improved ranking algorithm.
        
        Parameters
        ----------
        query : str
            Search query text.
        tenant_id : str  
            Tenant namespace identifier.
        limit : int, default=10
            Maximum number of results to return.
        min_similarity : float, default=0.7
            Minimum similarity threshold.
            
        Returns
        -------
        List[MemoryResult]
            Ranked list of matching memories.
            
        Raises
        ------
        ValidationError
            If query is empty or tenant_id is invalid.
        """
        # ✓ Input validation
        if not query.strip():
            raise ValidationError("Query cannot be empty")
        
        # ✓ Proper error handling    
        try:
            results = await self._perform_search(query, tenant_id, limit, min_similarity)
            # ✓ Logging for operations
            logger.info("Memory search completed", extra={
                "tenant_id": tenant_id,
                "query_length": len(query),
                "result_count": len(results)
            })
            return results
        except Exception as e:
            # ✓ Error logging with context
            logger.error("Memory search failed", extra={
                "tenant_id": tenant_id,
                "error": str(e)
            })
            raise
```

---

## Review Response Process

### [ ] Feedback Integration  
- [ ] **Address All Comments**: Respond to every review comment appropriately
- [ ] **Code Updates**: Make requested code changes with clear commits
- [ ] **Explanation**: Provide explanations for decisions where changes weren't made
- [ ] **Follow-up Questions**: Ask clarifying questions when feedback is unclear

### [ ] Communication
- [ ] **Timely Responses**: Respond to reviews within 24 hours during business days
- [ ] **Professional Tone**: Maintain constructive and professional communication
- [ ] **Context Sharing**: Provide additional context when helpful for reviewers
- [ ] **Gratitude**: Thank reviewers for their time and feedback

```markdown
# Example review response:

## Response to Review Comments

### @reviewer1 - Line 45: Consider using async context manager
✅ **Implemented** - Changed to `async with` pattern as suggested. This ensures proper cleanup even if exceptions occur.

### @reviewer2 - Performance concern about N+1 queries  
✅ **Fixed** - Added batch loading using `select_related()` to reduce database calls from O(n) to O(1).

### @reviewer3 - Add input validation
❓ **Question** - The validation you mentioned is already present in the BaseModel. Are you referring to additional validation beyond Pydantic? Could you clarify which specific cases you're concerned about?

### @security-team - Potential SQL injection risk
✅ **Addressed** - Switched from string formatting to parameterized queries using SQLAlchemy's text() with bound parameters.

## Additional Changes Made
- Added more comprehensive tests based on feedback
- Updated documentation to clarify the new behavior
- Fixed typo in error message

Thanks everyone for the thorough review! 🙏
```

---

## Testing in Review

### [ ] Reviewer Testing
- [ ] **Checkout and Test**: Instructions for reviewers to test changes locally
- [ ] **Test Data**: Sample data or test cases provided for reviewers
- [ ] **Demo Environment**: Deploy to staging/demo environment for review
- [ ] **Video Demo**: Screen recording of functionality for complex changes

### [ ] Continuous Integration
- [ ] **All Checks Pass**: CI pipeline shows green status
- [ ] **Test Coverage**: Coverage reports show adequate test coverage
- [ ] **Performance Tests**: No performance regressions detected
- [ ] **Security Scan**: Security scanning tools show no new vulnerabilities

```bash
# CI/CD pipeline checks to verify:
# ✓ Linting (ruff, black, isort)
# ✓ Type checking (mypy)  
# ✓ Unit tests (pytest)
# ✓ Integration tests
# ✓ Security scan (bandit, safety)
# ✓ Dependency check
# ✓ Build verification
# ✓ Docker image build
```

---

## Pre-Merge Verification

### [ ] Final Checks
- [ ] **All Approvals**: Required number of approvals obtained from appropriate reviewers
- [ ] **Conversations Resolved**: All review conversations are marked as resolved
- [ ] **CI Status**: Final CI run passes all checks
- [ ] **Merge Conflicts**: No merge conflicts with target branch

### [ ] Documentation Updates
- [ ] **Changelog**: Entry added to CHANGELOG.md if applicable
- [ ] **API Documentation**: OpenAPI/Swagger specs updated if API changes made  
- [ ] **Migration Guide**: Database or configuration migrations documented
- [ ] **Release Notes**: Significant changes noted for next release

---

## Merge Strategy

### [ ] Merge Method Selection
- [ ] **Squash and Merge**: For feature branches with multiple commits (preferred)
- [ ] **Merge Commit**: For important branches that need commit history preserved
- [ ] **Rebase and Merge**: For clean linear history when appropriate
- [ ] **Fast-forward**: Only when branch is single commit ahead

```bash
# Choose appropriate merge strategy:

# Squash and merge (most common)
git checkout main
git merge --squash feature/memory-improvements
git commit -m "feat(memory): improve search ranking algorithm

Implements enhanced ranking using multiple similarity metrics
and user feedback to improve search relevance.

Closes #123"

# Regular merge commit (for important features)
git checkout main  
git merge --no-ff feature/major-architecture-change

# Rebase and merge (for clean history)
git checkout feature/small-fix
git rebase main
git checkout main
git merge --ff-only feature/small-fix
```

### [ ] Post-Merge Actions
- [ ] **Branch Cleanup**: Delete merged feature branch
- [ ] **Issue Closure**: Verify linked issues are automatically closed
- [ ] **Deployment**: Monitor deployment pipeline if auto-deploy is enabled
- [ ] **Notifications**: Notify stakeholders of significant changes

---

## Rollback Preparedness

### [ ] Rollback Plan
- [ ] **Revert Strategy**: Plan for how to revert changes if issues arise
- [ ] **Database Migrations**: Rollback scripts for schema changes
- [ ] **Configuration Changes**: Plan for reverting configuration updates
- [ ] **Monitoring**: Set up alerts for monitoring change impact

### [ ] Risk Mitigation
- [ ] **Feature Flags**: Use feature flags for risky changes when possible
- [ ] **Gradual Rollout**: Plan for gradual rollout to subset of users
- [ ] **Monitoring**: Enhanced monitoring during and after deployment
- [ ] **Hotfix Process**: Clear process for emergency fixes if needed

```python
# Example: Feature flag for risky changes
from somabrain.config import feature_flags

async def search_memories(query: str, tenant_id: str) -> List[MemoryResult]:
    if feature_flags.is_enabled("enhanced_search_ranking", tenant_id):
        # New improved search algorithm
        return await enhanced_search(query, tenant_id)
    else:
        # Fallback to stable algorithm
        return await standard_search(query, tenant_id)
```

---

## Review Quality Standards

### [ ] Reviewer Responsibilities
- [ ] **Thorough Review**: Review all changed lines, not just major changes
- [ ] **Test the Changes**: Actually run and test the code when possible
- [ ] **Constructive Feedback**: Provide specific, actionable feedback
- [ ] **Security Focus**: Look for potential security vulnerabilities
- [ ] **Performance Impact**: Consider performance implications of changes

### [ ] Code Review Best Practices
- [ ] **Understand Context**: Read related code and documentation
- [ ] **Question Assumptions**: Ask questions when logic isn't clear
- [ ] **Suggest Improvements**: Offer specific suggestions for improvement
- [ ] **Recognize Good Work**: Acknowledge good practices and clever solutions
- [ ] **Focus on Important Issues**: Distinguish between critical issues and style preferences

```markdown
# Examples of good review comments:

## 👍 Positive Feedback
"Nice use of the async context manager pattern here - this ensures proper cleanup even if an exception occurs."

## 🤔 Constructive Questions  
"Could you help me understand why we're using a thread pool here instead of native async? Is there blocking I/O that I'm missing?"

## 🔧 Specific Suggestions
"Consider using `functools.lru_cache` here since this function is called frequently with repeated inputs:
```python
@lru_cache(maxsize=128)
def calculate_similarity_score(text1: str, text2: str) -> float:
    # existing implementation
```"

## 🚨 Critical Issues
"This looks like it could lead to SQL injection. Consider using parameterized queries:
```python
# Instead of: f"SELECT * FROM memories WHERE content LIKE '{query}'"
# Use: "SELECT * FROM memories WHERE content LIKE %s", (f'%{query}%',)
```"
```

**Verification**: PR checklist is complete when all items are verified and the PR is successfully merged without issues.

---

**Common Errors**:

| Error | Solution |
|-------|----------|
| CI pipeline failures | Check logs and fix failing tests or linting issues |
| Merge conflicts | Rebase branch on latest target branch |
| Missing approvals | Ensure all required reviewers have approved |
| Test coverage drop | Add tests for new code paths |
| Documentation gaps | Update relevant documentation sections |

**References**:
- [Pre-Commit Checklist](pre-commit-checklist.md) for code preparation
- [Contribution Process](../../development-manual/contribution-process.md) for detailed workflow
- [Coding Standards](../../development-manual/coding-standards.md) for style guidelines
- [Team Collaboration](../team-collaboration.md) for communication best practices