# Global Documentation Style Guide

**Purpose**: Standardized formatting, terminology, and conventions for all SomaBrain documentation.

**Audience**: All contributors creating or maintaining documentation across the project.

**Prerequisites**: Basic understanding of Markdown and technical writing principles.

---

## Document Structure Standards

### File Organization Rules

#### Naming Conventions
- **File names**: `kebab-case` with `.md` extension (e.g., `memory-operations.md`)
- **Directory names**: Singular form, lowercase (e.g., `runbooks/`, `features/`)
- **Image files**: Descriptive names with component prefix (e.g., `architecture-overview.png`)
- **Code examples**: Numbered if multiple (e.g., `example-01-basic-usage.py`)

#### Front Matter (Required)
Every document must begin with this metadata block:
```markdown
# Document Title

**Purpose**: One sentence describing what this document accomplishes.

**Audience**: Who should read this document (be specific about roles/expertise).

**Prerequisites**: What knowledge, tools, or setup is required before reading.

---
```

#### Document Sections
Standard section order for all documents:
1. **Purpose statement** - What and why
2. **Quick Navigation** - Table of contents for complex docs
3. **Main content** - Core information organized logically
4. **Verification** - How to confirm success/understanding
5. **Common Errors** - Troubleshooting table
6. **References** - Links to related documents

### Content Guidelines

#### Writing Style
- **Active voice**: "Run the command" not "The command should be run"
- **Present tense**: "SomaBrain provides" not "SomaBrain will provide"
- **Imperative for instructions**: "Install Docker" not "You should install Docker"
- **Concise sentences**: Maximum 25 words per sentence
- **Conversational but professional**: Accessible to international readers

#### Technical Terminology
| Term | Correct Usage | Avoid |
|------|---------------|-------|
| SomaBrain | Always capitalize, no spaces | somabrain, Soma Brain, SOMABRAIN |
| API endpoints | Backticks: `GET /health` | Bold or plain text |
| Code variables | Backticks: `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` | ALL_CAPS without formatting |
| File paths | Backticks: `docs/user-manual/index.md` | Plain text paths |
| UI elements | Bold: **Save** button | Quotes or plain text |

---

## Markdown Formatting Standards

### Headers
```markdown
# Document Title (H1 - Only one per document)
## Major Section (H2)
### Subsection (H3)
#### Detail Section (H4)
```

### Code Blocks
Always specify language for syntax highlighting:
````markdown
```bash
# Shell commands with comments
docker compose up -d
```

```python
# Python code with meaningful examples
from somabrain import MemoryClient
client = MemoryClient()
```

```yaml
# YAML configuration files
apiVersion: apps/v1
kind: Deployment
```
````

### Links and References
- **Internal links**: Use relative paths from current file location
- **External links**: `[Link Text](https://example.com)`
- **Anchor links**: `[Section](#section-heading)` (lowercase, hyphens for spaces)
- **Reference style**: Use for repeated URLs:
  ```markdown
  See the [official docs][1] and [API reference][2].

  [1]: https://docs.somabrain.com
  [2]: https://api.somabrain.com
  ```

### Lists and Tables
```markdown
# Unordered lists - use for non-sequential items
- First item
- Second item
  - Nested item (2 spaces)
  - Another nested item

# Ordered lists - use for sequential steps
1. First step
2. Second step
3. Third step

# Tables - align headers with content
| Column Header | Another Header | Status |
|---------------|----------------|--------|
| Value 1       | Value 2        | ✅ Done |
| Value 3       | Value 4        | 🔄 In Progress |
```

### Emphasis and Formatting
```markdown
**Bold text** - for UI elements, important concepts
*Italic text* - for emphasis, first introduction of terms
`Inline code` - for variables, commands, file names
> Blockquotes - for important warnings or principles
```

---

## Content Types & Templates

### API Documentation Template
```markdown
## Endpoint Name

**Purpose**: Brief description of what this endpoint does.

### Request
```http
POST /api/endpoint
Content-Type: application/json
Authorization: Bearer {token}

{
  "parameter": "value",
  "required_field": "example"
}
```

### Response
```json
{
  "status": "success",
  "data": {
    "result": "value"
  }
}
```

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parameter` | string | Yes | What this parameter does |

### Error Responses
| Status Code | Description | Example |
|-------------|-------------|---------|
| 400 | Bad Request | Missing required parameter |
| 401 | Unauthorized | Invalid token |
```

### Runbook Template
```markdown
# Service Name Operations

**Purpose**: Operational procedures for [service] in production.

## Service Overview
- Brief description
- Key dependencies
- Scaling characteristics

## Health Monitoring
- Health check endpoints
- Key metrics to watch
- Normal operating ranges

## Common Incidents
### Issue Name
**Symptoms**: What users/operators observe
**Diagnosis**: How to investigate
**Resolution**: Step-by-step fix procedure

## Emergency Procedures
- Escalation contacts
- Rollback procedures
- Communication templates
```

### Tutorial Template
```markdown
# Tutorial Title

**Purpose**: Help users accomplish [specific goal].

**Time Required**: X minutes

**Prerequisites**: List specific requirements

## What You'll Learn
- Learning objective 1
- Learning objective 2

## Step 1: Action
Brief explanation of what we're doing and why.

```bash
# Command with explanation
command --option value
```

**Expected output:**
```
Sample output that users should see
```

## Verification
How to confirm this step worked correctly.

---

**Next Steps**: Link to related tutorials or advanced topics.
```

---

## Quality Standards

### Accuracy Requirements
- **Code examples must work**: Test all code blocks before publishing
- **Links must resolve**: Check all internal and external links
- **Screenshots current**: Update images when UI changes
- **Version compatibility**: Specify version requirements when relevant

### Accessibility Guidelines
- **Alt text required**: All images need descriptive alt text
- **Descriptive links**: Avoid "click here" - use descriptive text
- **Color independence**: Don't rely solely on color to convey information
- **Heading hierarchy**: Use proper H1-H6 nesting

### Review Checklist
Before publishing any documentation:

- [ ] **Purpose statement** clearly describes document goal
- [ ] **Audience** specifically identifies intended readers
- [ ] **Prerequisites** list all required knowledge/setup
- [ ] **Code examples** tested and working
- [ ] **All links** resolve correctly
- [ ] **Verification section** explains success criteria
- [ ] **Common errors** table addresses likely issues
- [ ] **References** link to related documentation
- [ ] **Spelling and grammar** checked
- [ ] **Markdown syntax** renders correctly

---

## Automation Tools

### Linting
All documentation must pass these automated checks:

```bash
# Markdown linting
markdownlint-cli2 "docs/**/*.md"

# Link checking
markdown-link-check docs/**/*.md

# Spell checking
cspell "docs/**/*.md"
```

### Auto-generation
Some content is automatically generated:

- **API Reference**: Generated from OpenAPI specification
- **Configuration Options**: Extracted from code annotations
- **Metrics Documentation**: Generated from Prometheus metrics
- **Error Codes**: Extracted from application error definitions

### CI Integration
Documentation builds run these validations:
1. Markdown linting for style compliance
2. Link validation for internal/external references
3. Spell checking with project dictionary
4. Code block syntax validation
5. Image optimization and alt-text verification

---

## Terminology Dictionary

### SomaBrain-Specific Terms
| Term | Definition | Usage |
|------|------------|-------|
| **Cognitive Memory** | Semantic memory system mimicking human-like recall | Use when describing core platform capability |
| **Hyperdimensional Computing** | Mathematical framework using high-dimensional vectors | Use for technical explanations |
| **Working Memory** | Fast, temporary memory cache for active operations | Distinguish from long-term memory |
| **Density Matrix** | Mathematical structure tracking memory relationships | Use in technical documentation |
| **Strict Mode** | Production configuration requiring real services | Always capitalize |

### Technical Terms
| Term | Definition | Usage |
|------|------------|-------|
| **Memory Operations** | Store (remember) and retrieve (recall) functions | User-facing terminology |
| **Semantic Similarity** | Mathematical measure of meaning similarity | Technical explanations |
| **Multi-tenant** | Architecture supporting isolated user spaces | System design discussions |
| **Audit Trail** | Immutable log of all operations | Security and compliance contexts |

### Avoid These Terms
| Don't Use | Use Instead | Reason |
|-----------|-------------|---------|
| "DB" or "database" | "memory store" or "storage" | SomaBrain is not a traditional database |
| "AI memory" | "cognitive memory" | More precise and distinctive |
| "Vector search" | "semantic recall" | Emphasizes cognitive vs. search functionality |
| "Cache" (for working memory) | "working memory" | Cache implies temporary/disposable |

---

**Verification**: All documentation follows this style guide and passes automated linting checks.

**Common Errors**:
- Missing purpose statement → Add required front matter to document start
- Broken internal links → Use relative paths and verify file structure
- Code blocks without language → Always specify language for syntax highlighting
- Inconsistent terminology → Consult terminology dictionary above

**References**:
- [Markdown Guide](https://www.markdownguide.org/) for syntax reference
- [Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/) for inclusive design
