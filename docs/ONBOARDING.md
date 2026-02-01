# Project Context & Mission

**Purpose**: Understanding SomaBrain's mission, goals, and business context for new team members.

**Audience**: New developers, agent coders, contractors, and stakeholders joining the project.

**Prerequisites**: Basic understanding of artificial intelligence and memory systems.

---

## What is SomaBrain?

SomaBrain is a **cognitive memory platform** that uses hyperdimensional computing to provide semantic memory storage and reasoning capabilities for AI agents and applications.

### Core Mission
> **Enable scalable, mathematically-sound cognitive memory for the next generation of AI systems.**

SomaBrain bridges the gap between traditional databases (exact match) and human-like memory (associative, contextual, and adaptive). It provides AI agents with the ability to:

- **Store experiences semantically** rather than as raw data
- **Recall relevant memories** based on context and similarity
- **Reason about relationships** between stored experiences
- **Adapt and learn** from memory interactions over time

---

## Business Context

### Market Problem
Current AI systems suffer from memory limitations:

1. **Static Knowledge**: Training data becomes outdated and cannot be updated easily
2. **No Episodic Memory**: AI cannot remember specific experiences or interactions
3. **Poor Context Retention**: Limited ability to maintain context across long conversations
4. **Scaling Challenges**: Memory requirements grow exponentially with agent complexity

### SomaBrain Solution
SomaBrain provides a **memory-as-a-service** platform that:

- **Scales horizontally** to support millions of concurrent agents
- **Maintains mathematical guarantees** for memory consistency and recall quality
- **Integrates easily** with existing AI frameworks and applications
- **Operates in real-time** with sub-second response times

### Target Markets

#### Primary Markets
1. **Enterprise AI Agents**: Customer service bots, virtual assistants, and task automation
2. **Developer Tools**: AI development platforms requiring persistent memory
3. **Gaming & Simulation**: NPCs and virtual characters with persistent personalities
4. **Research Institutions**: Cognitive computing and AI memory research

#### Use Cases
- **Customer Service**: Agents that remember previous interactions across channels
- **Personal Assistants**: AI that learns user preferences and maintains context
- **Educational Systems**: Adaptive learning that tracks student progress and understanding
- **Scientific Research**: Knowledge management systems for complex research domains

---

## Project Goals & Success Metrics

### Primary Goals

#### 1. Mathematical Correctness
- **Goal**: All cognitive operations must be mathematically sound and deterministic
- **Metrics**: Zero mathematical invariant violations in production
- **Status**: ✅ Achieved through property testing and strict-mode enforcement

#### 2. Production Scalability
- **Goal**: Support 1M+ concurrent memory operations per second
- **Metrics**: <100ms p95 latency at target throughput
- **Status**: 🔄 In progress, current capacity ~10K ops/sec

#### 3. Developer Experience
- **Goal**: Simple integration requiring <1 day for basic implementation
- **Metrics**: Time-to-first-success <4 hours for new developers
- **Status**: 🔄 In progress, currently ~8 hours

#### 4. Enterprise Reliability
- **Goal**: 99.9% uptime with comprehensive observability
- **Metrics**: SLA compliance, mean-time-to-resolution <30 minutes
- **Status**: 🔄 In progress, monitoring infrastructure 80% complete

### Key Performance Indicators (KPIs)

#### Technical KPIs
| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| API Response Time (p95) | <100ms | ~150ms | ⬇️ Improving |
| Memory Recall Accuracy | >95% | 97.3% | ➡️ Stable |
| System Uptime | 99.9% | 99.2% | ⬆️ Improving |
| Mathematical Invariant Violations | 0 | 0 | ➡️ Stable |

#### Business KPIs
| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| Developer Onboarding Time | <4 hours | ~8 hours | ⬇️ Improving |
| API Integration Success Rate | >90% | 76% | ⬆️ Improving |
| Memory Operations per Agent | 1000/day | 650/day | ⬆️ Growing |
| Agent Memory Retention | 30 days | 21 days | ⬆️ Growing |

---

## Stakeholder Landscape

### Internal Stakeholders

#### Engineering Team
- **Primary Contributors**: 8 full-time engineers
- **Specializations**: Cognitive computing, distributed systems, mathematics
- **Responsibilities**: Core platform development, algorithms, infrastructure

#### Product Team
-- **Product Manager**: Market requirements
- **UX/Developer Experience**: API design, documentation, developer tools
- **Technical Writers**: Documentation, tutorials, developer education

#### Leadership Team
- **CTO**: Technical vision and architecture decisions
- **CEO**: Business strategy and market positioning
- **Head of Engineering**: Resource allocation and technical execution

### External Stakeholders

#### Customers & Partners
- **Enterprise Customers**: Large-scale AI deployments requiring memory solutions
- **Developer Community**: Individual developers and small teams building AI applications
- **Technology Partners**: AI framework providers, cloud platforms, system integrators
- **Research Institutions**: Universities and labs advancing cognitive computing

#### Investors & Board
- **Seed Investors**: Early backers focused on technical feasibility
- **Series A Investors**: Growth-stage investors evaluating market opportunity
- **Technical Advisors**: Industry experts providing strategic guidance
- **Board of Directors**: Governance and strategic oversight

---

## Technical Philosophy

### Core Principles

#### 1. Mathematical Truth
> **"No mocking, no mimicking, no fake data - only real mathematical operations"**

- All algorithms implement genuine mathematical foundations
- No shortcuts or approximations that compromise correctness
- Property testing validates mathematical invariants continuously
- Production code paths identical to development/test paths

#### 2. Strict Mode Enforcement
> **"Production code must use real services - no stubs, no fallbacks"**

- `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` enforces production-grade execution
- No silent degradation or stub usage in production environments
- Fail-fast approach to surface configuration and integration issues
- Comprehensive audit trails for all operations

#### 3. Observable Systems
> **"Every operation must be measurable, traceable, and debuggable"**

- Comprehensive metrics for all mathematical operations
- Structured logging with correlation IDs for request tracing
- Health checks that validate actual system capabilities
- Real-time monitoring of cognitive performance metrics

#### 4. Developer-Centric Design
> **"Cognitive computing should be as easy as using a database"**

- Simple REST API with intuitive endpoints
- Comprehensive documentation with working examples
- Local development environment setup in <10 minutes
- Clear error messages with actionable resolution steps

### Technology Choices

#### Why Hyperdimensional Computing?
- **Biological Inspiration**: Mirrors how human brains process and store memories
- **Mathematical Foundations**: Solid theoretical basis in high-dimensional mathematics
- **Scalability**: Operations remain efficient as memory size grows
- **Interpretability**: Memory representations can be analyzed and understood

#### Why Python & FastAPI?
- **Developer Familiarity**: Largest AI/ML developer community
- **Rich Ecosystem**: Extensive libraries for mathematics and machine learning
- **Performance**: Fast enough with proper optimization, easy to profile and optimize
- **Maintainability**: Clean, readable code that new developers can quickly understand

#### Why Strict Real Mode?
- **Production Reliability**: No hidden fallbacks or degraded functionality
- **Debugging Simplicity**: Production issues reproduce exactly in development
- **Mathematical Integrity**: Prevents subtle bugs from stub/mock interactions
- **Operational Confidence**: What you test is exactly what runs in production

---

## Project History & Evolution

### Timeline

#### Phase 1: Research & Foundations (2024 Q1-Q2)
- Mathematical foundations research and algorithm development
- Core hyperdimensional computing primitives implementation
- Property testing framework for mathematical invariants
- Initial API design and proof-of-concept

#### Phase 2: Platform Development (2024 Q3-Q4)
- Production-grade FastAPI service implementation
- Multi-tenant working memory system
- Comprehensive observability and monitoring
- Docker-based development and deployment infrastructure

#### Phase 3: Scale & Polish (2025 Q1-Q2) - **Current Phase**
- Performance optimization and horizontal scaling
- Developer experience improvements and documentation
- Enterprise features (auth, audit, compliance)
- Community building and open-source preparation

#### Phase 4: Market Expansion (2025 Q3-Q4) - **Planned**
- Cloud-native managed service offering
- Integration with major AI frameworks (LangChain, LlamaIndex, etc.)
- Enterprise sales and customer success programs
- Advanced cognitive reasoning capabilities

### Key Milestones Achieved
- ✅ Mathematical correctness validated through property testing
- ✅ Production-grade infrastructure with comprehensive monitoring
- ✅ Multi-tenant architecture supporting isolated memory spaces
- ✅ Sub-second memory operations at moderate scale (10K ops/sec)
- ✅ Developer-friendly local setup with Docker Compose

### Current Challenges
- 🔄 Scaling performance to 1M+ operations per second
- 🔄 Reducing developer onboarding time from 8 hours to <4 hours
- 🔄 Building enterprise sales and go-to-market capabilities
- 🔄 Establishing open-source community and contribution processes

---

## Success Stories & Impact

### Internal Wins
- **Zero Mathematical Bugs**: No production incidents caused by algorithmic errors
- **Fast Developer Onboarding**: New team members productive within 1 week
- **Reliable CI/CD**: All deployments pass comprehensive mathematical validation
- **Strong Team Culture**: Engineering team aligned on quality and mathematical rigor

### Customer Impact
- **Research Institution A**: 40% improvement in AI agent context retention
- **Enterprise Customer B**: Reduced memory-related latency by 60%
- **Developer Community**: 500+ successful integrations in beta program
- **Academic Papers**: 3 publications citing SomaBrain's mathematical approach

---

**Verification**: New team members understand project mission and can articulate core value proposition.

**Common Questions**:
- "How is this different from vector databases?" → See [Domain Knowledge](domain-knowledge.md) for technical differentiators
- "What's the business model?" → Memory-as-a-service with usage-based pricing
- "Who are the main competitors?" → Pinecone, Weaviate, but focused on cognitive vs. semantic search

**References**:
- [Codebase Walkthrough](codebase-walkthrough.md) for technical architecture understanding
- [Domain Knowledge](domain-knowledge.md) for deep technical concepts
- [Team Collaboration](team-collaboration.md) for working with the team
- [First Contribution](first-contribution.md) for getting started with code contributions
# Team Collaboration

**Purpose**: Comprehensive guide to communication channels, collaboration tools, and team processes for effective work on SomaBrain.

**Audience**: Team members, contributors, and collaborators working on SomaBrain project.

**Prerequisites**: Basic understanding of the project from [Project Context](project-context.md) and completed [Local Setup](../development/local-setup.md).

---

## Communication Channels

### Primary Channels

**GitHub Issues and Discussions**:
- **Purpose**: Technical discussions, bug reports, feature requests
- **When to use**: Code-related questions, project planning, public discussions
- **Response time**: 24-48 hours for maintainers
- **Link**: https://github.com/somabrain/somabrain/issues

**Slack Workspace** (Internal Team):
- **Purpose**: Real-time communication, quick questions, team coordination
- **Channels**:
  - `#general` - General project discussion
  - `#development` - Technical development chat
  - `#support` - Help and troubleshooting
  - `#random` - Non-work related chat
- **When to use**: Quick questions, urgent issues, team building
- **Response time**: During business hours (9 AM - 6 PM your timezone)

**Discord Server** (Community):
- **Purpose**: Community discussions, contributor support, open collaboration
- **Channels**:
  - `#welcome` - New member introductions
  - `#general-discussion` - Project-related discussions
  - `#development-help` - Technical assistance
  - `#showcase` - Share your work and achievements
- **When to use**: Community engagement, getting help, collaboration
- **Link**: https://discord.gg/somabrain

**Email** (Private/Sensitive):
- **Purpose**: Security issues, private concerns, administrative matters
- **Contact**: security@somabrain.com, team@somabrain.com
- **When to use**: Security vulnerabilities, licensing questions, private feedback

### Communication Guidelines

**Response Time Expectations**:
| Channel | Response Time | Escalation |
|---------|---------------|------------|
| GitHub Issues | 24-48 hours | Mention maintainer directly |
| Slack/Discord | 2-4 hours (business hours) | Switch to GitHub issue |
| Email | 2-3 business days | Follow up after 1 week |
| Security Email | Same day | Call emergency contact |

**Message Quality Standards**:
- **Be Specific**: Include context, error messages, steps to reproduce
- **Be Respectful**: Assume positive intent, use inclusive language
- **Be Patient**: Allow time for responses, people are in different timezones
- **Be Helpful**: Share solutions when you find them, help others

---

## Team Structure and Roles

### Core Team Roles

**Project Maintainers**:
- **Responsibilities**: Code review, architecture decisions, release management
- **Members**: @alice-maintainer, @bob-architect, @charlie-lead
- **Contact**: Via GitHub mentions or Slack DMs
- **Decision Authority**: Technical direction, breaking changes, major features

**Senior Contributors**:
- **Responsibilities**: Code review, mentoring, feature development
- **Recognition**: Consistent high-quality contributions over 6+ months
# (Removed roadmap reference)
- **Contact**: Via GitHub or community channels

**Contributors**:
- **Responsibilities**: Feature development, bug fixes, documentation
- **Everyone**: All community members who contribute code or documentation
- **Recognition**: Contributor acknowledgments, community recognition
- **Growth Path**: Senior Contributor → Maintainer with sustained contribution

**Community Members**:
- **Responsibilities**: Testing, feedback, issue reporting, discussions
- **Welcome**: Anyone interested in SomaBrain
- **Participation**: GitHub discussions, Discord, issue reports

### Specialized Roles

**Security Team** (@security-team):
- **Responsibilities**: Security review, vulnerability response, audit coordination
- **Contact**: security@somabrain.com (private), @security-team (GitHub)
- **Authority**: Security policy decisions, vulnerability disclosure

**Documentation Team** (@docs-team):
- **Responsibilities**: Documentation quality, user experience, tutorials
- **Contact**: Via GitHub issues with `documentation` label
- **Focus**: User onboarding, API documentation, guides and tutorials

**Performance Team** (@performance-team):
- **Responsibilities**: Performance monitoring, optimization, benchmarking
- **Contact**: Via GitHub issues with `performance` label
- **Focus**: Database optimization, API performance, scalability

---

## Development Workflows

### Sprint Planning (Bi-weekly)

**Schedule**: Every other Monday, 10 AM PST
**Duration**: 2 hours
**Participants**: Core team + interested contributors
**Format**: Video call + GitHub Projects

**Agenda**:
1. **Previous Sprint Review** (30 min)
   - Demo completed features
   - Review metrics and performance
   - Discuss blockers and challenges

2. **Current Sprint Planning** (60 min)
   - Prioritize GitHub issues
   - Assign issues to contributors
   - Estimate effort and timeline
   - Identify dependencies

3. **Technical Discussion** (30 min)
   - Architecture decisions
   - Breaking changes review
   - Performance improvements
   - Security considerations

**Artifacts**:
- Sprint milestone in GitHub
- Updated project board
- Meeting notes in GitHub Discussions

### Daily Standups (Optional)

**Schedule**: Monday/Wednesday/Friday, 9 AM PST
**Duration**: 15 minutes
**Format**: Slack thread or quick video call
**Participants**: Active contributors (voluntary)

**Format**:
```
## Daily Standup - [Date]

**@username**:
- ✅ Yesterday: Completed memory search API tests
- 🔄 Today: Working on documentation updates
- 🚧 Blockers: Waiting for database migration review

**@another-contributor**:
- ✅ Yesterday: Fixed performance regression in vector encoding
- 🔄 Today: Investigating Redis caching optimization
- 🚧 Blockers: None

Add your update below! 👇
```

### Code Review Process

**Review Assignment**:
1. **Automatic**: GitHub automatically assigns 2 reviewers
2. **Self-Assignment**: Team members can assign themselves
3. **Expertise-Based**: Assign specialists for specific areas (security, performance)
4. **Load Balancing**: Distribute reviews evenly among maintainers

**Review Checklist**:
```markdown
## Code Review Checklist

### Functionality
- [ ] Code solves the stated problem
- [ ] Edge cases are handled appropriately
- [ ] Error handling is comprehensive
- [ ] Performance impact is acceptable

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Functions are well-documented
- [ ] Variable names are clear and descriptive
- [ ] Code is DRY (Don't Repeat Yourself)

### Testing
- [ ] Unit tests cover new functionality
- [ ] Integration tests verify component interaction
- [ ] Test cases include edge cases and error scenarios
- [ ] All tests pass in CI/CD pipeline

### Security
- [ ] Input validation is present and correct
- [ ] No sensitive data in logs or responses
- [ ] Authentication/authorization properly implemented
- [ ] SQL injection and XSS vulnerabilities checked

### Documentation
- [ ] API changes documented
- [ ] User-facing changes have updated guides
- [ ] Code comments explain complex logic
- [ ] Changelog updated for user-facing changes
```

**Review Response Guidelines**:
```markdown
## Providing Feedback

**Constructive Comments**:
✅ "Consider using a more specific exception type here for better error handling"
✅ "This function could benefit from some inline documentation"
✅ "Great implementation! One small suggestion for performance..."

**Avoid**:
❌ "This is wrong"
❌ "Bad code"
❌ "Why did you do this?"

**Receiving Feedback**:
✅ "Thanks for the suggestion! I'll update the implementation"
✅ "Good point about edge cases, I'll add tests for that"
✅ "I chose this approach because X, but I see your point about Y"

**Disagreement Resolution**:
1. Discuss in PR comments with technical reasoning
2. Escalate to maintainer if no consensus
3. Video call for complex architectural discussions
4. Document decisions for future reference
```

---

## Issue Management

### Issue Lifecycle

```mermaid
graph TD
    A[Issue Created] --> B[Triage]
    B --> C{Valid Issue?}
    C -->|No| D[Close with explanation]
    C -->|Yes| E[Label and Prioritize]
    E --> F{Needs More Info?}
    F -->|Yes| G[Request Information]
    G --> H[Wait for Response]
    H --> I{Response Received?}
    I -->|No| J[Close Stale]
    I -->|Yes| E
    F -->|No| K[Ready for Work]
    K --> L[Assigned to Contributor]
    L --> M[In Progress]
    M --> N[Pull Request Created]
    N --> O[Code Review]
    O --> P{Approved?}
    P -->|No| Q[Request Changes]
    Q --> M
    P -->|Yes| R[Merged]
    R --> S[Issue Closed]
```

### Issue Labels

**Priority Labels**:
- `priority/critical` - Security issues, production bugs
- `priority/high` - Important features, significant bugs
- `priority/medium` - Regular features and improvements
- `priority/low` - Nice-to-have features, minor bugs

**Type Labels**:
- `type/bug` - Something isn't working correctly
- `type/feature` - New functionality request
- `type/enhancement` - Improvement to existing functionality
- `type/documentation` - Documentation improvements
- `type/performance` - Performance-related changes
- `type/security` - Security-related issues

**Status Labels**:
- `status/triage` - Needs initial review and labeling
- `status/blocked` - Cannot proceed due to external dependency
- `status/in-progress` - Actively being worked on
- `status/needs-review` - Ready for code review
- `status/stale` - No activity for 30+ days

**Difficulty Labels**:
- `good-first-issue` - Great for newcomers
- `difficulty/easy` - 1-2 hours of work
- `difficulty/medium` - 1-2 days of work
- `difficulty/hard` - 1+ weeks of work

### Issue Templates

**Bug Report Template**:
```markdown
## Bug Description
Brief description of the issue.

## Steps to Reproduce
1. Go to...
2. Click on...
3. See error

## Expected Behavior
What should have happened.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.11.2]
- SomaBrain version: [e.g. 1.2.3]
- Browser (if applicable): [e.g. Chrome 120]

## Additional Context
- Error logs
- Screenshots
- Related issues
```

**Feature Request Template**:
```markdown
## Problem Statement
What problem does this feature solve?

## Proposed Solution
Detailed description of the proposed feature.

## Alternative Solutions
Other approaches considered.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Additional Context
- Mockups or diagrams
- Related features
- Implementation ideas
```

---

## Collaboration Tools

### GitHub Projects

**Project Boards**:
# (Removed roadmap reference)
- **Current Sprint**: Active work items and progress tracking
- **Backlog Grooming**: Issue prioritization and refinement

**Board Columns**:
```
Backlog → Triaged → In Progress → In Review → Testing → Done
```

**Automation Rules**:
- Issues automatically move to "In Progress" when assigned
- PRs move to "In Review" when opened
- Completed PRs move issues to "Done"

### Documentation Collaboration

**Shared Documents**:
- **Technical RFCs**: Architecture decision documents
- **Meeting Notes**: Sprint planning and technical discussions
- **Runbooks**: Operational procedures and troubleshooting
- **Design Documents**: Feature specifications and wireframes

**Documentation Workflow**:
1. **Draft**: Create initial document in Google Docs (or similar)
2. **Review**: Share with team for feedback and iteration
3. **Finalize**: Move to official documentation repository
4. **Maintain**: Keep updated with code changes

### Monitoring and Metrics

**Team Dashboards**:
- **Development Metrics**: PR velocity, review time, merge rate
- **Code Quality**: Test coverage, linting violations, security issues
- **Community Health**: Issue response time, contributor growth
- **Performance**: API response times, error rates, system health

**Regular Reviews**:
- **Weekly**: Quick metrics review in team sync
- **Monthly**: Detailed analysis and process improvements
- **Quarterly**: Strategic review and goal setting

---

## Conflict Resolution

### Disagreement Types

**Technical Disagreements**:
1. **Code Implementation**: Different approaches to solving a problem
2. **Architecture Decisions**: High-level design choices
3. **Technology Choices**: Library/framework selection
4. **Performance Trade-offs**: Speed vs. maintainability decisions

**Process Disagreements**:
1. **Timeline Conflicts**: Deadline vs. quality tensions
2. **Priority Disputes**: Feature importance disagreements
3. **Resource Allocation**: Time and effort distribution
4. **Quality Standards**: Acceptable quality levels

### Resolution Process

**Level 1: Direct Discussion**
```markdown
## Steps for Direct Resolution

1. **Acknowledge**: "I see we have different views on this approach"
2. **Understand**: "Help me understand your perspective on X"
3. **Explain**: "My concern with approach Y is..."
4. **Collaborate**: "What if we tried Z as a compromise?"
5. **Document**: Record the decision and reasoning
```

**Level 2: Maintainer Mediation**
- **When**: Direct discussion doesn't reach consensus within 2 days
- **Process**: Mention maintainer in GitHub discussion
- **Timeline**: Maintainer provides decision within 48 hours
- **Authority**: Technical maintainer decision is final

**Level 3: Team Discussion**
- **When**: Significant architectural or policy decisions
- **Format**: Team meeting or async GitHub discussion
- **Participants**: All maintainers + senior contributors
- **Timeline**: One week for discussion, then formal decision

**Level 4: Project Lead Decision**
- **When**: Deadlock at team level or critical urgency
- **Authority**: Project lead (@project-lead) makes final call
- **Timeline**: 24-48 hours for critical decisions
- **Documentation**: Decision rationale published for transparency

### Best Practices

**Healthy Debate Guidelines**:
```markdown
## Effective Technical Discussions

**Do**:
✅ Focus on technical merits and trade-offs
✅ Provide concrete examples and data
✅ Consider multiple perspectives
✅ Be willing to change your mind
✅ Separate ideas from people ("the approach" not "your approach")

**Don't**:
❌ Make it personal or about individual competence
❌ Dismiss concerns without addressing them
❌ Use authority or seniority to shut down discussion
❌ Rehash previously decided issues without new information
❌ Block progress indefinitely
```

**Compromise Strategies**:
- **Timeboxed Experiments**: Try approach A for 2 weeks, then evaluate
- **Hybrid Solutions**: Combine elements from different proposals
- **Phased Implementation**: Start with simpler approach, evolve later
- **A/B Testing**: Implement both approaches and measure results

---

## Remote Work Guidelines

### Asynchronous Collaboration

**Time Zone Considerations**:
- **Core Hours**: 9 AM - 12 PM PST when most team overlap occurs
- **Meeting Scheduling**: Use shared calendar with timezone display
- **Documentation**: Always document decisions and discussions
- **Response Expectations**: 24-hour response time across timezones

**Effective Async Communication**:
```markdown
## Good Async Messages

**Provide Context**:
"I'm working on the memory search API (PR #123) and noticed that..."

**Be Specific**:
"The test on line 45 of test_memory.py is failing with error: 'AttributeError: ...'"

**Include Next Steps**:
"I'll try approach X tomorrow. If that doesn't work, should I explore Y instead?"

**Set Expectations**:
"This is blocking my progress, could someone review by EOD Thursday?"
```

### Meeting Etiquette

**Video Call Best Practices**:
- **Camera On**: Encourages engagement and connection
- **Mute When Not Speaking**: Reduces background noise
- **Good Setup**: Stable internet, clear audio, proper lighting
- **Engagement**: Active participation, avoid multitasking

**Meeting Preparation**:
```markdown
## Meeting Checklist

**Before the Meeting**:
- [ ] Review agenda and prepare talking points
- [ ] Test audio/video setup
- [ ] Have relevant documents/code ready
- [ ] Prepare questions or discussion topics

**During the Meeting**:
- [ ] Take notes on decisions and action items
- [ ] Speak up if you have concerns or questions
- [ ] Stay focused on the topic
- [ ] Respect time limits

**After the Meeting**:
- [ ] Send summary of decisions and action items
- [ ] Update GitHub issues/projects as needed
- [ ] Follow up on assigned tasks
```

### Knowledge Sharing

**Documentation Culture**:
- **Write Everything Down**: Decisions, rationale, context
- **Keep It Updated**: Documentation rots quickly without maintenance
- **Make It Searchable**: Use consistent terminology and tagging
- **Review Regularly**: Quarterly documentation audits

**Knowledge Transfer Methods**:
- **Code Comments**: Explain complex logic and decisions
- **Architectural Decision Records (ADRs)**: Document significant decisions
- **Pair Programming**: Share knowledge through collaboration
- **Tech Talks**: Present interesting findings or solutions

**Verification**: Team collaboration is effective when communication is clear, conflicts are resolved constructively, and knowledge is shared efficiently.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Messages lost in wrong channel | Use GitHub for code, Slack for quick chat |
| Timezone confusion in meetings | Always specify timezone, use UTC for clarity |
| Decisions made without documentation | Record all technical decisions in GitHub |
| Review bottlenecks | Distribute review load, set response expectations |
| Knowledge silos | Regular pair programming and documentation |

**References**:
- [First Contribution](first-contribution.md) for hands-on collaboration practice
- [Domain Knowledge](domain-knowledge.md) for technical context in discussions
- [Contribution Process](../development/contribution-process.md) for detailed workflow
- [Coding Standards](../development/coding-standards.md) for quality standards# 🧠 SomaBrain Quick Start Guide

> **Cognitive Runtime Engine** - Get SomaBrain running in 10 minutes

---

## Prerequisites

| Component | Minimum Version |
|-----------|-----------------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| Python | 3.11+ |
| RAM | 16GB |

---

## Step 1: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/somatech/somabrain.git
cd somabrain

# Copy environment template
cp .env.example .env
```

### Required Environment Variables

```bash
# Database (use shared SOMA Stack database)
SOMA_DB_HOST=localhost
SOMA_DB_PORT=20432
SOMA_DB_NAME=somabrain
SOMA_DB_USER=postgres
SOMA_DB_PASSWORD=somastack2024

# Redis
REDIS_URL=redis://:somastack2024@localhost:20379/1

# Memory Service
SOMA_MEMORY_URL=http://localhost:9595
SOMA_MEMORY_API_TOKEN=your-token

# Milvus (Vector DB)
MILVUS_HOST=localhost
MILVUS_PORT=20530
```

---

## Step 2: Start Infrastructure

### With SomaAgent01 Stack (Recommended)

```bash
# Start from somaAgent01 directory
cd ../somaAgent01
docker compose up -d
```

### Standalone Mode

```bash
docker compose up -d
```

---

## Step 3: Verify Health

```bash
# Check API health
curl http://localhost:30101/health

# Expected response:
# {"status": "healthy", "component": "somabrain"}
```

---

## Step 4: Run Migrations

```bash
# With Tilt (automatic, from SomaAgent01)
tilt up

# Manual
python manage.py migrate --database=somabrain
```

---

## Port Namespace Reference

**SomaBrain uses port 30xxx:**

| Service | Port |
|---------|------|
| SomaBrain API | 30101 |
| gRPC (internal) | 30102 |
| Metrics | 30103 |

**Dependencies (from SomaAgent01 20xxx):**
- PostgreSQL: 20432
- Redis: 20379
- Milvus: 20530

---

## Step 5: Development Workflow

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Run development server
uvicorn somabrain.asgi:application --host 0.0.0.0 --port 30101 --reload
```

---

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/{id}/sessions` | POST | Create agent session |
| `/api/v1/agents/{id}/chat` | POST | Chat with agent (SSE streaming) |
| `/api/v1/health` | GET | Health check |
| `/api/v1/metrics` | GET | Prometheus metrics |

---

## Architecture Overview

```
SomaBrain Cognitive Modules
├── amygdala.py      - Emotional processing
├── hippocampus.py   - Memory formation
├── prefrontal.py    - Executive function
├── thalamus.py      - Sensory relay
├── basal_ganglia.py - Motor control
├── wm.py            - Working memory (22KB)
├── quantum.py       - Quantum operations (16KB)
└── sdr.py           - Sparse distributed representations
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Milvus" | Ensure SomaAgent01 stack is running |
| "Database does not exist" | Run `make reset-infra` from SomaAgent01 |
| "Memory service unavailable" | Start SomaFractalMemory first |

---

## Related Documentation

- [SomaAgent01 Quick Start](https://github.com/somatechlat/somaAgent01/blob/main/docs/QUICKSTART.md)
- [Deployment Guide](deployment/docker_deployment.md)
- [Coding Standards](development/coding-standards.md)

---

**Version**: 1.0.0 | **Last Updated**: 2026-01-04
# Security Hardening Guide

**Purpose**: Understand security controls and best practices in SomaBrain.

## Authentication (Code-Verified)

**Implementation**: `somabrain/auth.py`

### Bearer Token Auth

```python
def require_auth(request: Request, cfg: Config) -> None:
    """Validate Bearer token from Authorization header."""
    # Checks: Authorization: Bearer <token>
    # Validates against cfg.api_token or JWT
```

### Admin Auth

```python
def require_admin_auth(request: Request, cfg: Config) -> None:
    """Require admin-level authentication."""
    # Additional checks for admin endpoints
```

### JWT Support

**Config** (from `somabrain/config.py`):

```python
jwt_secret: Optional[str] = None
jwt_public_key_path: Optional[str] = None
jwt_issuer: Optional[str] = None
jwt_audience: Optional[str] = None
```

**Environment Variables**:
```bash
SOMABRAIN_JWT_SECRET="<secret>"
SOMABRAIN_JWT_PUBLIC_KEY_PATH="/path/to/key.pem"
SOMABRAIN_JWT_ISSUER="somabrain"
SOMABRAIN_JWT_AUDIENCE="api"
```

## Tenant Isolation

**Implementation**: `somabrain/tenant.py`

```python
def get_tenant(request: Request, default_namespace: str) -> TenantContext:
    """Extract tenant ID from X-Tenant-ID header or JWT claims."""
    # Returns: TenantContext(tenant_id, namespace)
```

**Headers**:
```
X-Tenant-ID: sandbox
```

**Isolation Guarantees**:
- Working memory is per-tenant (`mt_wm.recall(tenant_id, ...)`)
- HRR context is per-tenant (`mt_ctx.cleanup(tenant_id, ...)`)
- Adaptation state is per-tenant (Redis keys: `adaptation:state:{tenant_id}`)

## Rate Limiting

**Implementation**: `somabrain/ratelimit.py`

**Config** (from `somabrain/config.py`):

```python
rate_rps: float = 50.0      # Requests per second
rate_burst: int = 100       # Burst capacity
```

**Usage** (from `somabrain/app.py`):

```python
if not rate_limiter.allow(ctx.tenant_id):
    raise HTTPException(status_code=429, detail="rate limit exceeded")
```

## Quotas

**Implementation**: `somabrain/quotas.py`

**Config**:

```python
write_daily_limit: int = 10000  # Max writes per tenant per day
```

**Usage**:

```python
if not quotas.allow_write(ctx.tenant_id, 1):
    raise HTTPException(status_code=429, detail="daily write quota exceeded")
```

## OPA Policy Enforcement

**Service**: `somabrain_opa` (Docker Compose)

**Port**: 30104 (host) → 8181 (container)

**Policies**: `ops/opa/policies/`

**Middleware**: `somabrain/api/middleware/opa.py`

**Health Check**:

```python
opa_ok = opa_client.is_ready()  # Required for readiness
```

## Input Validation

**Implementation**: `somabrain/app.py` (CognitiveInputValidator)

### Text Validation

```python
SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.,!?\'\"()/:_@-]+$")
MAX_TEXT_LENGTH = 10000

def validate_text_input(text: str, field_name: str = "text") -> str:
    """Validate text input for cognitive processing."""
    # Checks: length, safe characters
```

### Coordinate Validation

```python
def validate_coordinates(coords: tuple) -> tuple:
    """Validate coordinate tuples for brain processing."""
    # Checks: exactly 3 floats, reasonable magnitude
```

### Query Sanitization

```python
def sanitize_query(query: str) -> str:
    """Sanitize and prepare query for cognitive processing."""
    # Removes: <>, javascript:, data: patterns
```

## Security Middleware

**Implementation**: `somabrain/app.py` (SecurityMiddleware)

**Blocked Patterns**:

```python
suspicious_patterns = [
    re.compile(r"union\s+select", re.IGNORECASE),  # SQL injection
    re.compile(r";\s*drop", re.IGNORECASE),        # SQL injection
    re.compile(r"<script", re.IGNORECASE),         # XSS
    re.compile(r"eval\s*\(", re.IGNORECASE),       # Code injection
]
```

**Response**: 403 Forbidden

## Docker Security (docker-compose.yml)

### Capability Dropping

```yaml
cap_drop: ["ALL"]  # Drop all Linux capabilities
```

### Read-Only Filesystem

```yaml
read_only: true  # Prevent runtime file modifications
```

### No New Privileges

```yaml
security_opt:
  - no-new-privileges:true  # Prevent privilege escalation
```

### Tmpfs Mounts

```yaml
tmpfs:
  - /app/logs  # Writable logs without persistent storage
  - /tmp       # Temporary files
```

## Secrets Management

### Environment Variables (Development)

```bash
# ✅ CORRECT - Use placeholders in docs
SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN>"

# ❌ WRONG - Never commit real tokens
SOMABRAIN_MEMORY_HTTP_TOKEN="sk-prod-abc123..."
```

### Production Secrets

**Recommended**: Use external secret managers

- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets

**Never**:
- Hardcode in source code
- Commit to git
- Log to stdout

## Audit Logging

**Implementation**: `somabrain/audit.py`

**Kafka Topic**: `soma.audit`

**Events Logged**:
- Admin actions (`log_admin_action`)
- Authentication failures
- Policy violations

**Example**:

```python
audit.log_admin_action(request, "neuromodulators_set", {
    "tenant": tenant_id,
    "new_state": {...}
})
```

## Network Security (Docker Compose)

**Internal Network**: `somabrain_net` (bridge)

**Exposed Ports** (host access):
- 9696: API (required)
- 30100-30108: Infrastructure (optional, can be removed in prod)

**Internal-Only Services**:
- Kafka broker: `somabrain_kafka:9092` (not exposed to host by default)
- Redis: `somabrain_redis:6379` (exposed for dev, should be internal in prod)

## Security Checklist

### Before Deployment

- [ ] Rotate all default credentials
- [ ] Enable JWT authentication (`SOMABRAIN_JWT_SECRET`)
- [ ] Configure OPA policies
- [ ] Set rate limits per tenant
- [ ] Enable audit logging to Kafka
- [ ] Review exposed ports
- [ ] Use read-only filesystem
- [ ] Drop all capabilities
- [ ] Enable TLS for external endpoints

### Runtime Monitoring

- [ ] Monitor failed auth attempts
- [ ] Track rate limit violations
- [ ] Alert on circuit breaker opens
- [ ] Review audit logs daily
- [ ] Check OPA policy decisions

## Key Files to Read

1. `somabrain/auth.py` - Authentication logic
2. `somabrain/tenant.py` - Tenant isolation
3. `somabrain/ratelimit.py` - Rate limiting
4. `somabrain/quotas.py` - Quota enforcement
5. `somabrain/app.py` - Input validation, security middleware
6. `ops/opa/policies/` - OPA policy definitions
7. `docker-compose.yml` - Container security settings
# Agent Zero: First Steps

**Purpose**: Get an AI agent up and running with SomaBrain in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- External memory service running at `http://localhost:9595`
- 2GB RAM available

## Quick Start (Code-Verified Steps)

### 1. Clone and Start

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d
```

**What This Does** (from `docker-compose.yml`):
- Starts Redis on port 30100
- Starts Kafka on port 30102
- Starts OPA on port 30104
- Starts Postgres on port 30106
- Starts Prometheus on port 30105
- Starts SomaBrain API on port 9696

### 2. Verify Health

```bash
curl http://localhost:9696/health | jq .
```

**Expected Response**:

```json
{
  "ok": true,
  "ready": true,
  "components": {
    "memory": {"http": true, "ok": true},
    "api_version": 1
  },
  "predictor_ok": true,
  "memory_ok": true,
  "embedder_ok": true,
  "kafka_ok": true,
  "postgres_ok": true,
  "opa_ok": true
}
```

### 3. Store Your First Memory

```bash
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "task": "The Eiffel Tower is in Paris",
      "memory_type": "episodic"
    }
  }'
```

**Response**:

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns"
}
```

### 4. Recall the Memory

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Where is the Eiffel Tower?",
    "top_k": 3
  }' | jq .
```

**Response**:

```json
{
  "wm": [
    {
      "score": 0.92,
      "payload": {
        "task": "The Eiffel Tower is in Paris",
        "memory_type": "episodic"
      }
    }
  ],
  "memory": [...],
  "namespace": "somabrain_ns"
}
```

## Understanding the Response

### Working Memory (wm)

- **Source**: In-memory cache (`mt_wm`)
- **Capacity**: 64 items per tenant (default)
- **Scoring**: UnifiedScorer (cosine + FD + recency)
- **Fast**: No external service call

### Long-Term Memory (memory)

- **Source**: External memory service
- **Capacity**: Unlimited (backend-dependent)
- **Persistence**: Survives restarts
- **Slower**: HTTP call to backend

## Configuration Basics

### Environment Variables

**Required**:

```bash
SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:9595"
SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN_HERE>"  # Required - set your actual token
```

**Optional**:

```bash
SOMABRAIN_MODE="full-local"  # or "prod"
SOMABRAIN_PREDICTOR_PROVIDER="mahal"  # mahal|slow|llm
SOMABRAIN_EMBED_PROVIDER="tiny"  # tiny|openai|...
```

### Config File (config.yaml)

```yaml
wm_size: 64
embed_dim: 256
use_hrr: false
rate_rps: 50.0
```

**Location**: Project root

**Loading**: Automatic via `load_config()` in `somabrain/config.py`

## Common Issues

### 1. Memory Backend Not Available

**Error**:

```json
{
  "detail": {"message": "memory backend unavailable"}
}
```

**Fix**:

```bash
# Check memory service is running
curl http://localhost:9595/health

# Verify endpoint in config
echo $SOMABRAIN_MEMORY_HTTP_ENDPOINT
```

### 2. Health Check Fails

**Symptom**: `"ready": false`

**Debug**:

```bash
# Check individual components
curl http://localhost:9696/health | jq '{
  memory_ok,
  kafka_ok,
  postgres_ok,
  opa_ok,
  embedder_ok,
  predictor_ok
}'
```

**Fix**: Start missing services

```bash
docker compose up -d somabrain_kafka somabrain_postgres somabrain_opa
```

### 3. Rate Limit Exceeded

**Error**: `429 Too Many Requests`

**Fix**: Adjust rate limits

```bash
export SOMABRAIN_RATE_RPS=100
export SOMABRAIN_RATE_BURST=200
docker compose restart somabrain_app
```

## Next Steps

1. **Read [propagation-agent.md](propagation-agent.md)** - Deep dive into memory operations
2. **Read [monitoring-agent.md](monitoring-agent.md)** - Set up observability
3. **Read [security-hardening.md](security-hardening.md)** - Secure your deployment
4. **Explore API** - Try `/context/evaluate`, `/context/feedback`, `/plan/suggest`

## API Endpoints Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/remember` | POST | Store memory |
| `/recall` | POST | Retrieve memory |
| `/context/evaluate` | POST | Build context |
| `/context/feedback` | POST | Update weights |
| `/plan/suggest` | POST | Generate plan |
| `/neuromodulators` | GET/POST | Get/set neuromodulator state |

## Code Entry Points

- **Main App**: `somabrain/app.py`
- **Config**: `somabrain/config.py`
- **Memory**: `somabrain/memory/`
- **Quantum/HRR**: `somabrain/quantum.py`
- **Scoring**: `somabrain/scoring.py`
- **Learning**: `somabrain/learning/adaptation.py`

## Testing Your Setup

```bash
# Run integration tests
pytest tests/integration/

# Run core tests
pytest tests/core/

# Check code quality
ruff check somabrain/
mypy somabrain/
```

## Getting Help

- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory
- **Tests**: `tests/` directory (usage examples)
- **Issues**: GitHub Issues

## Success Criteria

You're ready to build when:

- ✅ Health endpoint returns `"ready": true`
- ✅ You can store and recall a memory
- ✅ Metrics endpoint returns Prometheus data
- ✅ All Docker services are healthy
- ✅ You understand the basic API flow
# Agent Onboarding Guide

**Purpose**: Enable AI agents to understand and work with the SomaBrain codebase effectively.

## Quick Facts (Code-Verified)

| Property | Value | Source |
|----------|-------|--------|
| **Main API File** | `somabrain/app.py` | FastAPI application |
| **API Port** | 9696 (host and container) | `docker-compose.yml` |
| **Config System** | `somabrain/config.py` | Dataclass-based with env overrides |
| **Memory Dimension** | 256 (default `embed_dim`) | `Config` dataclass |
| **HRR Dimension** | 8192 (default `hrr_dim`) | `Config` dataclass |
| **Working Memory Size** | 64 (default `wm_size`) | `Config` dataclass |

## Core Components (Actual Locations)

### 1. API Layer
- **File**: `somabrain/app.py`
- **Framework**: FastAPI
- **Key Endpoints**:
  - `POST /remember` - Store memory
  - `POST /recall` - Retrieve memory
  - `POST /context/evaluate` - Build context
  - `POST /context/feedback` - Update weights
  - `GET /health` - Health check

### 2. Configuration
- **File**: `somabrain/config.py`
- **Class**: `Config` (dataclass)
- **Loading**: `load_config()` function
- **Env Prefix**: `SOMABRAIN_`

### 3. Quantum/HRR Layer
- **File**: `somabrain/quantum.py`
- **Class**: `QuantumLayer`
- **Math**: BHDC (Binary Hyperdimensional Computing)
- **Operations**: `bind()`, `unbind()`, `superpose()`

### 4. Memory System
- **Superposed Trace**: `somabrain/memory/superposed_trace.py`
- **Hierarchical**: `somabrain/memory/hierarchical.py`
- **Classes**: `SuperposedTrace`, `TieredMemory`

### 5. Scoring
- **File**: `somabrain/scoring.py`
- **Class**: `UnifiedScorer`
- **Components**: Cosine + FD + Recency

### 6. Learning/Adaptation
- **File**: `somabrain/learning/adaptation.py`
- **Class**: `AdaptationEngine`
- **Weights**: Retrieval (α, β, γ, τ) + Utility (λ, μ, ν)

## Environment Variables (Real Defaults)

```bash
# Memory Backend (REQUIRED)
SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:9595"
SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN_HERE>"  # Required - set your actual token

# Redis
SOMABRAIN_REDIS_URL="redis://localhost:30100"

# Kafka
SOMABRAIN_KAFKA_URL="somabrain_kafka:9092"

# Postgres
SOMABRAIN_POSTGRES_DSN="postgresql://soma:soma@localhost:30106/somabrain"

# OPA
SOMABRAIN_OPA_URL="http://localhost:30104"

# Mode
SOMABRAIN_MODE="full-local"  # or "prod"

# Predictor
SOMABRAIN_PREDICTOR_PROVIDER="mahal"  # mahal|slow|llm
```

## Docker Compose Ports (Verified)

| Service | Host Port | Container Port | Internal Name |
|---------|-----------|----------------|---------------|
| API | 9696 | 9696 | somabrain_app |
| Redis | 30100 | 6379 | somabrain_redis |
| Kafka | 30102 | 9092 | somabrain_kafka |
| OPA | 30104 | 8181 | somabrain_opa |
| Prometheus | 30105 | 9090 | somabrain_prometheus |
| Postgres | 30106 | 5432 | somabrain_postgres |
| Schema Registry | 30108 | 8081 | somabrain_schema_registry |

## Next Steps

1. Read [propagation-agent.md](propagation-agent.md) for memory operations
2. Read [monitoring-agent.md](monitoring-agent.md) for observability
3. Read [security-hardening.md](security-hardening.md) for security practices

## Code Navigation Tips

- **Start here**: `somabrain/app.py` (main FastAPI app)
- **Config**: `somabrain/config.py` (all settings)
- **Math**: `somabrain/quantum.py` (BHDC operations)
- **Memory**: `somabrain/memory/` (storage abstractions)
- **Tests**: `tests/` (examples of usage)
# Propagation Agent Guide

**Purpose**: Understand memory storage and retrieval operations in SomaBrain.

## Memory Operations (Code-Verified)

### 1. Remember (Store Memory)

**Endpoint**: `POST /remember`

**Implementation**: `somabrain/app.py` line ~2800

**Request Body** (two formats supported):

```json
{
  "payload": {
    "task": "Paris is the capital of France",
    "memory_type": "episodic",
    "timestamp": 1234567890
  }
}
```

OR (legacy format):

```json
{
  "task": "Paris is the capital of France",
  "memory_type": "episodic"
}
```

**What Happens** (actual code flow):

1. **Auth Check**: `require_auth(request, cfg)` - validates Bearer token
2. **Tenant Resolution**: `get_tenant(request, cfg.namespace)` - extracts tenant ID
3. **Rate Limiting**: `rate_limiter.allow(ctx.tenant_id)` - checks RPS limits
4. **Quota Check**: `quotas.allow_write(ctx.tenant_id, 1)` - daily write limit
5. **Embedding**: `embedder.embed(text)` - generates vector
6. **Memory Service**: `memsvc.aremember(key, payload)` - stores to backend
7. **WM Admission**: `mt_wm.admit(ctx.tenant_id, wm_vec, payload)` - adds to working memory
8. **HRR Context**: `mt_ctx.admit(ctx.tenant_id, anchor_id, hrr_vec)` - if HRR enabled

**Response**:

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns",
  "trace_id": "...",
  "deadline_ms": null,
  "idempotency_key": null
}
```

### 2. Recall (Retrieve Memory)

**Endpoint**: `POST /recall`

**Implementation**: `somabrain/app.py` line ~2400

**Request**:

```json
{
  "query": "capital of France",
  "top_k": 3
}
```

**What Happens** (actual code flow):

1. **Embedding**: `embedder.embed(text)` - query vector
2. **WM Recall**: `mt_wm.recall(ctx.tenant_id, wm_qv, top_k)` - working memory hits
3. **LTM Recall**: `_recall_ltm(mem_client, text, top_k, ...)` - long-term memory
4. **Scoring**: `_score_memory_candidate(...)` - composite scoring (cosine + FD + recency)
5. **HRR Cleanup**: `mt_ctx.cleanup(ctx.tenant_id, hrr_qv)` - if enabled
6. **Caching**: Results cached in `_recall_cache` with 2s TTL

**Response**:

```json
{
  "wm": [
    {"score": 0.95, "payload": {"task": "..."}}
  ],
  "memory": [
    {"task": "Paris is the capital of France", "timestamp": 1234567890}
  ],
  "results": [...],  // alias for memory
  "namespace": "somabrain_ns",
  "trace_id": "..."
}
```

## Scoring System (UnifiedScorer)

**File**: `somabrain/scoring.py`

**Components** (actual weights from code):

```python
w_cosine: float = 0.6      # Cosine similarity weight
w_fd: float = 0.25          # Frequent-Directions weight
w_recency: float = 0.15     # Recency boost weight
recency_tau: float = 32.0   # Decay time constant
```

**Formula**:

```
score = w_cosine * cosine(q, c) + w_fd * fd_sim(q, c) + w_recency * exp(-age/tau)
```

## Working Memory (MultiTenantWM)

**File**: `somabrain/mt_wm.py`

**Default Capacity**: 64 items per tenant (`wm_size` in config)

**Operations**:
- `admit(tenant_id, vec, payload)` - add item
- `recall(tenant_id, query_vec, top_k)` - retrieve similar items
- `items(tenant_id)` - list all items

## HRR Context (MultiTenantHRRContext)

**File**: `somabrain/mt_context.py`

**Purpose**: Cleanup/disambiguation using hyperdimensional anchors

**Config** (from `HRRContextConfig`):
- `max_anchors`: 10000 (default)
- `decay_lambda`: 0.0 (no decay by default)
- `min_confidence`: 0.0 (accept all matches)

**Operations**:
- `admit(tenant_id, anchor_id, hrr_vec)` - register anchor
- `cleanup(tenant_id, query_hrr)` - find best matching anchor
- `analyze(tenant_id, hrr_vec)` - get score + margin

## Memory Service Client

**File**: `somabrain/services/memory_service.py`

**Backend**: HTTP-based external memory service

**Required Config**:
```python
http.endpoint = "http://localhost:9595"  # SOMABRAIN_MEMORY_HTTP_ENDPOINT
http.token = "<YOUR_TOKEN_HERE>"          # SOMABRAIN_MEMORY_HTTP_TOKEN (required)
```

**Circuit Breaker** (fail-fast):
- `_failure_threshold`: 3 consecutive failures
- `_reset_interval`: 60 seconds
- Raises `RuntimeError` when circuit open

## Example: Complete Remember Flow

```python
# 1. Client sends request
POST /remember
{
  "payload": {
    "task": "Learn Python",
    "memory_type": "episodic"
  }
}

# 2. API processes (somabrain/app.py)
# - Auth: require_auth()
# - Tenant: get_tenant() → "sandbox"
# - Rate limit: rate_limiter.allow("sandbox") → True
# - Quota: quotas.allow_write("sandbox", 1) → True
# - Embed: embedder.embed("Learn Python") → [256-dim vector]
# - Store: memsvc.aremember("Learn Python", payload)
# - WM: mt_wm.admit("sandbox", vec, payload)
# - HRR: mt_ctx.admit("sandbox", "Learn Python", hrr_vec)

# 3. Response
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns"
}
```

## Testing Memory Operations

```bash
# Store a memory
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "Test memory", "memory_type": "episodic"}}'

# Recall it
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "Test memory", "top_k": 3}'
```

## Key Files to Read

1. `somabrain/app.py` - API endpoints (remember, recall)
2. `somabrain/scoring.py` - UnifiedScorer implementation
3. `somabrain/mt_wm.py` - Working memory
4. `somabrain/services/memory_service.py` - Backend client
5. `somabrain/quantum.py` - HRR operations
# Monitoring Agent Guide

**Purpose**: Understand observability, metrics, and health checks in SomaBrain.

## Health Endpoint (Code-Verified)

**Endpoint**: `GET /health`

**Implementation**: `somabrain/app.py` line ~1900

**Response Structure** (actual fields from code):

```json
{
  "ok": true,
  "components": {
    "memory": {"http": true, "ok": true},
    "wm_items": "tenant-scoped",
    "api_version": 1
  },
  "namespace": "somabrain_ns",
  "ready": true,
  "predictor_ok": true,
  "memory_ok": true,
  "embedder_ok": true,
  "kafka_ok": true,
  "postgres_ok": true,
  "opa_ok": true,
  "external_backends_required": true,
  "predictor_provider": "mahal",
  "embedder": {"provider": "tiny", "dim": 256},
  "memory_circuit_open": false
}
```

## Readiness Checks (Actual Logic)

**From `somabrain/app.py` health endpoint**:

```python
# Backend enforcement requires:
predictor_ok = predictor_provider not in ("stub", "baseline")
memory_ok = memory_backend.health()["http"] == True
embedder_ok = embedder is not None
kafka_ok = check_kafka(kafka_url)  # somabrain/healthchecks.py
postgres_ok = check_postgres(pg_dsn)  # somabrain/healthchecks.py
opa_ok = opa_client.is_ready()

# Overall readiness:
ready = predictor_ok and memory_ok and embedder_ok and kafka_ok and postgres_ok and opa_ok
```

## Metrics Endpoint

**Endpoint**: `GET /metrics`

**Implementation**: `somabrain/metrics.py`

**Format**: Prometheus text format

**Key Metrics** (actual from code):

### Request Metrics
```
somabrain_http_request_duration_seconds{method="POST",path="/recall"}
somabrain_http_requests_total{method="POST",path="/recall",status="200"}
```

### Memory Metrics
```
somabrain_wm_hits_total
somabrain_wm_misses_total
somabrain_wm_utilization
somabrain_recall_cache_hit_total{cohort="baseline"}
somabrain_recall_cache_miss_total{cohort="baseline"}
```

### Scoring Metrics
```
somabrain_scorer_component{component="cosine"}
somabrain_scorer_component{component="fd"}
somabrain_scorer_component{component="recency"}
somabrain_scorer_final
```

### Learning Metrics
```
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="alpha"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="beta"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="gamma"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="tau"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="lambda"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="mu"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="nu"}
```

### HRR Metrics
```
somabrain_hrr_cleanup_calls_total
somabrain_hrr_cleanup_used_total
somabrain_hrr_cleanup_score
somabrain_hrr_anchor_size
somabrain_hrr_context_saturation
somabrain_hrr_rerank_applied_total
```

## Prometheus Configuration

**File**: `ops/prometheus/etc/prometheus.yml`

**Scrape Config**:

```yaml
scrape_configs:
  - job_name: 'somabrain'
    static_configs:
      - targets: ['somabrain_app:9696']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Health Check Implementation

**File**: `somabrain/healthchecks.py`

### Kafka Check

```python
def check_kafka(kafka_url: str) -> bool:
    """Verify Kafka broker is reachable."""
    # Actual implementation uses AdminClient
    # Returns True if broker responds
```

### Postgres Check

```python
def check_postgres(dsn: str) -> bool:
    """Verify Postgres connection."""
    # Actual implementation uses psycopg2
    # Returns True if connection succeeds
```

## Circuit Breaker (Memory Service)

**File**: `somabrain/services/memory_service.py`

**State Variables** (class-level):

```python
_circuit_open: bool = False
_failure_count: int = 0
_last_failure_time: float = 0.0
_failure_threshold: int = 3
_reset_interval: int = 60  # seconds
```

**Logic**:

```python
# On failure:
_failure_count += 1
if _failure_count >= _failure_threshold:
    _circuit_open = True
    _last_failure_time = time.time()

# On success:
_failure_count = 0
_circuit_open = False

# Auto-reset after interval:
if _circuit_open and (time.time() - _last_failure_time) > _reset_interval:
    _circuit_open = False
    _failure_count = 0
```

## Logging Configuration

**File**: `somabrain/app.py` (setup_logging function)

**Log Levels**:
- `INFO`: General system events
- `DEBUG`: Cognitive processing details
- `ERROR`: Error handling

**Log Output**:
- Console (stdout)
- File: `/app/logs/somabrain.log` (if writable)

**Format**:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Observability Stack (Docker Compose)

| Component | Port | Purpose |
|-----------|------|---------|
| Prometheus | 30105 | Metrics collection |
| Jaeger | 30011 | Distributed tracing |
| Kafka Exporter | 30103 | Kafka metrics |
| Postgres Exporter | 30107 | Postgres metrics |

## Example: Monitoring Workflow

```bash
# 1. Check health
curl http://localhost:9696/health | jq .

# 2. Verify readiness
curl http://localhost:9696/health | jq '.ready'

# 3. Scrape metrics
curl http://localhost:9696/metrics | grep somabrain_

# 4. Query Prometheus
curl 'http://localhost:30105/api/v1/query?query=somabrain_http_requests_total'

# 5. Check circuit breaker
curl http://localhost:9696/health | jq '.memory_circuit_open'
```

## Alert Conditions (Recommended)

Based on actual metrics:

```yaml
# High error rate
- alert: HighErrorRate
  expr: rate(somabrain_http_requests_total{status=~"5.."}[5m]) > 0.05

# Memory backend down
- alert: MemoryBackendDown
  expr: somabrain_health_memory_ok == 0

# Circuit breaker open
- alert: CircuitBreakerOpen
  expr: somabrain_memory_circuit_open == 1

# WM utilization high
- alert: WMUtilizationHigh
  expr: somabrain_wm_utilization > 0.9
```

## Key Files to Read

1. `somabrain/app.py` - Health endpoint implementation
2. `somabrain/metrics.py` - Metrics definitions
3. `somabrain/healthchecks.py` - Health check functions
4. `somabrain/services/memory_service.py` - Circuit breaker
5. `ops/prometheus/etc/prometheus.yml` - Prometheus config
# Domain Knowledge

**Purpose**: Deep technical understanding of SomaBrain's cognitive memory platform, including mathematical foundations, architectural decisions, and business logic.

**Audience**: Developers who need comprehensive understanding of hyperdimensional computing, vector mathematics, and cognitive reasoning systems.

**Prerequisites**: Strong programming background, familiarity with [Codebase Walkthrough](codebase-walkthrough.md), and basic linear algebra knowledge.

---

## Cognitive Memory Fundamentals

### What is Cognitive Memory?

**Definition**: Cognitive memory systems store and retrieve information based on semantic meaning rather than exact matches, mimicking how human memory works.

**Key Characteristics**:
- **Associative**: Related concepts are stored and retrieved together
- **Fuzzy Matching**: Finds similar content even without exact keywords
- **Context Aware**: Considers metadata, timing, and relationships
- **Scalable**: Performance remains stable as memory grows
- **Persistent**: Maintains knowledge across sessions and updates

**Traditional vs. Cognitive Storage**:

| Traditional Database | Cognitive Memory |
|---------------------|------------------|
| Exact keyword matching | Semantic similarity |
| Structured queries | Natural language queries |
| Fixed schema | Flexible metadata |
| Boolean results | Scored relevance |
| Linear search complexity | Logarithmic search complexity |

### SomaBrain's Approach

**Hyperdimensional Computing (HDC)**:
- **Vector Representations**: Convert text to high-dimensional numerical vectors
- **Semantic Preservation**: Similar meanings → similar vectors
- **Mathematical Operations**: Use vector arithmetic for reasoning
- **Efficient Storage**: Optimized for similarity computations

**Mathematical Foundation**:
```python
# Vector similarity using cosine distance
def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Compute semantic similarity between two memory vectors.

    Returns value between -1 (opposite) and 1 (identical).
    Values > 0.7 typically indicate strong semantic relationship.
    """
    dot_product = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)

    if norms == 0:
        return 0.0

    return dot_product / norms

# Memory storage process
def store_memory(content: str, metadata: dict) -> str:
    """
    Complete memory storage pipeline.

    1. Text preprocessing (cleaning, normalization)
    2. Vector encoding using transformer models
    3. Metadata enrichment and validation
    4. Database storage with indexing
    5. Cache population for fast retrieval
    """

    # 1. Preprocess content
    clean_content = preprocess_text(content)

    # 2. Encode to vector using sentence transformers
    vector = sentence_transformer.encode(clean_content)

    # 3. Enrich metadata with automatic tags
    enriched_metadata = enrich_metadata(metadata, clean_content)

    # 4. Store in PostgreSQL with pgvector
    memory_id = database.store_memory(
        content=clean_content,
        vector=vector,
        metadata=enriched_metadata,
        tenant_id=current_tenant
    )

    # 5. Update cache for fast access
    cache.store_memory_summary(memory_id, vector, enriched_metadata)

    return memory_id
```

---

## 🔬 Mathematical Foundations & Validation

| Invariant | Description | Enforcement |
| --- | --- | --- |
| Density matrix trace | `abs(trace(ρ) - 1) < 1e-4` | `somabrain/memory/density.py` renormalizes after each update. |
| PSD stability | Negative eigenvalues are clipped so ρ stays PSD | `DensityMatrix.project_psd()` trims the spectrum. |
| Scorer bounds | Component weights stay within configured bounds | `somabrain/scoring.py` clamps weights and exports metrics. |
| Strict-mode audit | Stub usage raises `RuntimeError` | `_audit_stub_usage` inside `somabrain/memory_client.py`. |
| Governance | Rate limits, OPA policy, neuromodulator feedback | Middleware stack inside `somabrain.app` and controls modules. |

All mathematical invariants are monitored through `/metrics` with Prometheus integration.

---

## Vector Encoding Architecture

### Transformer Models

**Current Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384 (balanced performance/accuracy)
- **Context Length**: 256 tokens (~200 words)
- **Training**: Optimized for semantic textual similarity
- **Performance**: ~50ms encoding time, ~95% accuracy on benchmarks

**Alternative Models**:

| Model | Dimensions | Speed | Accuracy | Use Case |
|-------|------------|-------|----------|----------|
| all-MiniLM-L6-v2 | 384 | Fast | High | Production default |
| all-mpnet-base-v2 | 768 | Medium | Very High | Quality-critical applications |
| distilbert-base-nli | 768 | Medium | High | Research and development |
| paraphrase-multilingual | 512 | Slow | High | Multi-language support |

### Vector Operations

**Encoding Pipeline**:
```python
class VectorEncoder:
    """
    High-performance text-to-vector encoding system.

    Features:
    - Batch processing for efficiency
    - GPU acceleration when available
    - Automatic text preprocessing
    - Vector normalization for consistency
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize encoder with specified transformer model."""
        self.model = SentenceTransformer(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

        # Enable mixed precision for speed
        if self.device == "cuda":
            self.model.half()

    def encode_single(self, text: str) -> np.ndarray:
        """Encode single text to normalized vector."""

        # Preprocess text
        clean_text = self.preprocess_text(text)

        # Handle empty text
        if not clean_text.strip():
            return np.zeros(self.model.get_sentence_embedding_dimension())

        # Encode with model
        vector = self.model.encode(
            clean_text,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization
        )

        return vector.astype(np.float32)

    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Efficiently encode multiple texts."""

        if not texts:
            return np.array([])

        # Preprocess all texts
        clean_texts = [self.preprocess_text(text) for text in texts]

        # Filter empty texts
        valid_indices = [i for i, text in enumerate(clean_texts) if text.strip()]
        valid_texts = [clean_texts[i] for i in valid_indices]

        if not valid_texts:
            empty_vector = np.zeros(self.model.get_sentence_embedding_dimension())
            return np.array([empty_vector] * len(texts))

        # Batch encode
        vectors = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(valid_texts) > 100
        )

        # Reconstruct full result array
        result = np.zeros((len(texts), vectors.shape[1]), dtype=np.float32)
        for i, valid_idx in enumerate(valid_indices):
            result[valid_idx] = vectors[i]

        return result

    def preprocess_text(self, text: str) -> str:
        """Clean and normalize text for encoding."""

        # Basic cleaning
        text = text.strip()

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Handle special characters and encoding
        text = text.encode('utf-8', errors='ignore').decode('utf-8')

        # Truncate to model limits (with some buffer)
        max_length = 200  # Leave room for tokenization overhead
        words = text.split()
        if len(words) > max_length:
            text = ' '.join(words[:max_length])

        return text
```

### Similarity Computation

**Distance Metrics**:
```python
def compute_similarities(query_vector: np.ndarray, memory_vectors: np.ndarray) -> np.ndarray:
    """
    Compute similarity scores between query and memory vectors.

    Uses cosine similarity for semantic relationship measurement.
    Optimized for large-scale vector operations.
    """

    # Ensure vectors are normalized
    query_norm = query_vector / np.linalg.norm(query_vector)
    memory_norms = memory_vectors / np.linalg.norm(memory_vectors, axis=1, keepdims=True)

    # Compute cosine similarities using matrix multiplication
    similarities = np.dot(memory_norms, query_norm)

    return similarities

def similarity_search(
    query_vector: np.ndarray,
    memory_vectors: np.ndarray,
    metadata: List[dict],
    k: int = 10,
    threshold: float = 0.2
) -> List[Tuple[int, float]]:
    """
    Find k most similar memories above threshold.

    Returns list of (memory_index, similarity_score) tuples.
    """

    # Compute all similarities
    similarities = compute_similarities(query_vector, memory_vectors)

    # Filter by threshold
    valid_indices = np.where(similarities >= threshold)[0]
    valid_similarities = similarities[valid_indices]

    # Sort by similarity (descending)
    sorted_indices = np.argsort(valid_similarities)[::-1]

    # Return top k results
    results = []
    for i in sorted_indices[:k]:
        memory_idx = valid_indices[i]
        similarity = valid_similarities[i]
        results.append((memory_idx, similarity))

    return results
```

---

## Database Architecture

### PostgreSQL with pgvector

**Schema Design**:
```sql
-- Main memory storage table
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    vector_encoding VECTOR(384) NOT NULL,  -- pgvector extension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT vector_dimension_check CHECK (array_length(vector_encoding, 1) = 384)
);

-- Indexes for performance
CREATE INDEX CONCURRENTLY idx_memories_tenant_created
    ON memories (tenant_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_memories_metadata_gin
    ON memories USING GIN (metadata);

-- Vector similarity index (HNSW for approximate nearest neighbor)
CREATE INDEX CONCURRENTLY idx_memories_vector_hnsw
    ON memories USING hnsw (vector_encoding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Exact vector index for smaller datasets
CREATE INDEX CONCURRENTLY idx_memories_vector_ivfflat
    ON memories USING ivfflat (vector_encoding vector_cosine_ops)
    WITH (lists = 100);
```

**Query Optimization**:
```sql
-- Optimized similarity search query
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    id,
    content,
    metadata,
    1 - (vector_encoding <=> $1::vector) as similarity_score
FROM memories
WHERE
    tenant_id = $2
    AND 1 - (vector_encoding <=> $1::vector) >= $3  -- Threshold filter
    AND metadata @> $4::jsonb  -- Metadata filter using GIN index
ORDER BY vector_encoding <=> $1::vector  -- pgvector distance operator
LIMIT $5;

-- Query plan analysis shows:
-- 1. Index scan on tenant_id (fast tenant isolation)
-- 2. Vector similarity using HNSW index (sub-linear search)
-- 3. GIN index for metadata filtering (efficient JSON queries)
-- 4. Minimal memory usage with streaming results
```

### Connection Pooling and Performance

**Connection Management**:
```python
class DatabasePool:
    """
    High-performance PostgreSQL connection pool.

    Features:
    - Async connections using asyncpg
    - Connection health monitoring
    - Query timeout handling
    - Prepared statement caching
    - Transaction management
    """

    def __init__(self, database_url: str, pool_size: int = 20):
        self.database_url = database_url
        self.pool_size = pool_size
        self.pool = None

    async def initialize(self):
        """Create connection pool with optimized settings."""

        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,                    # Minimum connections
            max_size=self.pool_size,       # Maximum connections
            max_queries=50000,             # Queries per connection
            max_inactive_connection_lifetime=300,  # 5 minute timeout
            command_timeout=30,            # Query timeout
            server_settings={
                'application_name': 'somabrain_api',
                'tcp_keepalives_idle': '600',
                'tcp_keepalives_interval': '30',
                'tcp_keepalives_count': '3'
            }
        )

        # Prepare common queries for performance
        async with self.pool.acquire() as conn:
            await self.prepare_statements(conn)

    async def prepare_statements(self, conn):
        """Prepare frequently-used queries for better performance."""

        # Memory storage query
        await conn.prepare("""
            INSERT INTO memories (tenant_id, content, metadata, vector_encoding)
            VALUES ($1, $2, $3, $4::vector)
            RETURNING id
        """)

        # Similarity search query
        await conn.prepare("""
            SELECT id, content, metadata,
                   1 - (vector_encoding <=> $1::vector) as similarity_score
            FROM memories
            WHERE tenant_id = $2
              AND 1 - (vector_encoding <=> $1::vector) >= $3
            ORDER BY vector_encoding <=> $1::vector
            LIMIT $4
        """)

    async def execute_similarity_search(
        self,
        query_vector: np.ndarray,
        tenant_id: str,
        threshold: float,
        limit: int
    ) -> List[dict]:
        """Execute optimized similarity search."""

        async with self.pool.acquire() as conn:
            # Use prepared statement for performance
            rows = await conn.fetch(
                "similarity_search_query",
                query_vector.tolist(),  # Convert numpy to list for postgres
                tenant_id,
                threshold,
                limit
            )

            return [dict(row) for row in rows]
```

---

## Cognitive Reasoning System

### Reasoning Chain Architecture

**Multi-Step Reasoning**:
```python
class CognitiveReasoner:
    """
    Multi-step reasoning system that chains memory retrieval
    with logical inference to answer complex questions.
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.reasoning_cache = LRUCache(maxsize=1000)

    async def generate_reasoning_chain(
        self,
        context: str,
        evidence_memories: List[Memory],
        reasoning_depth: str = "detailed"
    ) -> ReasoningChain:
        """
        Generate step-by-step reasoning from memories and context.

        Process:
        1. Extract key concepts from context
        2. Find supporting and contradicting evidence
        3. Build logical chain from premises to conclusion
        4. Assign confidence scores to each step
        5. Validate reasoning consistency
        """

        # Check cache first
        cache_key = self.hash_reasoning_input(context, evidence_memories)
        if cache_key in self.reasoning_cache:
            return self.reasoning_cache[cache_key]

        # Extract concepts and relationships
        concepts = await self.extract_concepts(context)
        relationships = await self.find_concept_relationships(concepts, evidence_memories)

        # Build reasoning steps
        reasoning_steps = []

        for concept in concepts:
            # Find supporting evidence
            supporting_memories = [
                m for m in evidence_memories
                if self.supports_concept(m, concept)
            ]

            if supporting_memories:
                step = ReasoningStep(
                    step_number=len(reasoning_steps) + 1,
                    concept=concept,
                    premise=self.extract_premise(supporting_memories),
                    evidence=supporting_memories,
                    confidence=self.calculate_confidence(supporting_memories),
                    reasoning_type="evidence_based"
                )
                reasoning_steps.append(step)

        # Generate conclusion
        conclusion = await self.synthesize_conclusion(
            context, reasoning_steps, reasoning_depth
        )

        reasoning_chain = ReasoningChain(
            context=context,
            steps=reasoning_steps,
            conclusion=conclusion,
            overall_confidence=self.calculate_chain_confidence(reasoning_steps),
            evidence_count=len(evidence_memories)
        )

        # Cache result
        self.reasoning_cache[cache_key] = reasoning_chain

        return reasoning_chain

    def calculate_confidence(self, memories: List[Memory]) -> float:
        """
        Calculate confidence score based on memory quality and consistency.

        Factors:
        - Number of supporting memories (more = higher confidence)
        - Similarity scores (higher = more relevant)
        - Memory age (recent = more reliable)
        - Source credibility (from metadata)
        - Consistency between memories
        """

        if not memories:
            return 0.0

        # Base confidence from similarity scores
        similarity_scores = [m.similarity_score for m in memories if m.similarity_score]
        avg_similarity = np.mean(similarity_scores) if similarity_scores else 0.5

        # Boost for multiple supporting memories
        memory_count_factor = min(len(memories) / 5.0, 1.0)  # Max boost at 5 memories

        # Age factor (newer memories are more reliable)
        age_factor = self.calculate_age_factor(memories)

        # Source credibility factor
        credibility_factor = self.calculate_credibility_factor(memories)

        # Consistency factor (similar memories saying same thing)
        consistency_factor = self.calculate_consistency_factor(memories)

        # Combine factors (weighted average)
        confidence = (
            0.3 * avg_similarity +
            0.2 * memory_count_factor +
            0.2 * age_factor +
            0.15 * credibility_factor +
            0.15 * consistency_factor
        )

        return min(confidence, 0.99)  # Cap at 99% confidence

    async def synthesize_conclusion(
        self,
        context: str,
        steps: List[ReasoningStep],
        depth: str
    ) -> ReasoningConclusion:
        """
        Synthesize final conclusion from reasoning steps.

        Uses logical inference rules to combine premises
        into coherent conclusions with appropriate confidence.
        """

        if not steps:
            return ReasoningConclusion(
                conclusion="Insufficient evidence for reasoning",
                confidence=0.0,
                reasoning_type="insufficient_evidence"
            )

        # Group steps by confidence level
        high_confidence_steps = [s for s in steps if s.confidence >= 0.7]
        medium_confidence_steps = [s for s in steps if 0.4 <= s.confidence < 0.7]

        # Build conclusion based on strongest evidence
        if high_confidence_steps:
            conclusion_text = self.build_strong_conclusion(
                context, high_confidence_steps, depth
            )
            confidence = np.mean([s.confidence for s in high_confidence_steps])
        elif medium_confidence_steps:
            conclusion_text = self.build_tentative_conclusion(
                context, medium_confidence_steps, depth
            )
            confidence = np.mean([s.confidence for s in medium_confidence_steps]) * 0.8
        else:
            conclusion_text = "Evidence suggests possible connection, but confidence is low"
            confidence = 0.3

        return ReasoningConclusion(
            conclusion=conclusion_text,
            confidence=confidence,
            supporting_steps=[s.step_number for s in high_confidence_steps],
            reasoning_type="synthesized"
        )
```

### Pattern Recognition

**Memory Pattern Analysis**:
```python
class PatternAnalyzer:
    """
    Analyzes patterns and relationships in stored memories
    to discover implicit knowledge and connections.
    """

    async def analyze_topic_clusters(
        self,
        memories: List[Memory],
        max_clusters: int = 10
    ) -> List[TopicCluster]:
        """
        Discover topic clusters using vector similarity and metadata.

        Uses hierarchical clustering on vector embeddings
        combined with metadata analysis for semantic grouping.
        """

        if len(memories) < 2:
            return []

        # Extract vectors and metadata
        vectors = np.array([m.vector_encoding for m in memories])
        metadata_features = self.extract_metadata_features(memories)

        # Combine vector and metadata features
        combined_features = np.hstack([vectors, metadata_features])

        # Perform clustering
        from sklearn.cluster import AgglomerativeClustering

        n_clusters = min(max_clusters, len(memories) // 3)  # At least 3 memories per cluster
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage='ward'
        )

        cluster_labels = clustering.fit_predict(combined_features)

        # Build cluster objects
        clusters = []
        for cluster_id in range(n_clusters):
            cluster_memories = [
                memories[i] for i, label in enumerate(cluster_labels)
                if label == cluster_id
            ]

            if len(cluster_memories) >= 2:  # Only meaningful clusters
                cluster = await self.build_topic_cluster(cluster_id, cluster_memories)
                clusters.append(cluster)

        return sorted(clusters, key=lambda c: c.coherence_score, reverse=True)

    async def detect_temporal_patterns(
        self,
        memories: List[Memory],
        time_window_days: int = 30
    ) -> List[TemporalPattern]:
        """
        Detect patterns in memory creation over time.

        Identifies:
        - Topic trends (increasing/decreasing interest)
        - Periodic patterns (weekly/monthly cycles)
        - Burst events (sudden activity spikes)
        - Knowledge evolution (concept development over time)
        """

        # Group memories by time windows
        time_groups = defaultdict(list)

        for memory in memories:
            # Convert to time window bucket
            bucket = self.get_time_bucket(memory.created_at, time_window_days)
            time_groups[bucket].append(memory)

        patterns = []

        # Analyze each time window
        for bucket, bucket_memories in time_groups.items():
            if len(bucket_memories) < 3:  # Need minimum for pattern detection
                continue

            # Extract topics and concepts
            topics = await self.extract_topics(bucket_memories)

            # Compare with previous time windows
            previous_bucket = bucket - timedelta(days=time_window_days)
            if previous_bucket in time_groups:
                previous_topics = await self.extract_topics(time_groups[previous_bucket])

                # Detect trends
                trend = self.analyze_topic_trend(topics, previous_topics)
                if trend.significance > 0.5:
                    pattern = TemporalPattern(
                        pattern_type="trend",
                        time_period=bucket,
                        description=trend.description,
                        confidence=trend.significance,
                        affected_memories=bucket_memories
                    )
                    patterns.append(pattern)

        return patterns
```

---

## Business Logic

### Multi-Tenancy Architecture

**Tenant Isolation**:
```python
class TenantManager:
    """
    Manages tenant isolation, quotas, and security policies.

    Ensures complete data isolation between tenants while
    maintaining performance and operational efficiency.
    """

    def __init__(self, database: DatabaseManager, cache: CacheManager):
        self.database = database
        self.cache = cache
        self.tenant_configs = {}

    async def validate_tenant_access(
        self,
        tenant_id: str,
        api_key: str,
        operation: str
    ) -> TenantContext:
        """
        Validate tenant access and return context with limits.

        Checks:
        - API key validity and permissions
        - Tenant exists and is active
        - Operation is allowed for tenant tier
        - Rate limits and quotas
        """

        # Check cache first
        cache_key = f"tenant_access:{tenant_id}:{api_key}"
        cached_context = await self.cache.get(cache_key)

        if cached_context and not self.is_cache_expired(cached_context):
            return cached_context

        # Validate API key
        tenant_config = await self.database.get_tenant_config(tenant_id)
        if not tenant_config:
            raise AuthenticationError(f"Tenant {tenant_id} not found")

        if not self.verify_api_key(api_key, tenant_config.api_key_hash):
            raise AuthenticationError("Invalid API key")

        # Check tenant status
        if tenant_config.status != "active":
            raise AuthorizationError(f"Tenant {tenant_id} is {tenant_config.status}")

        # Check operation permissions
        if not self.check_operation_permission(operation, tenant_config.tier):
            raise AuthorizationError(f"Operation {operation} not allowed for tier {tenant_config.tier}")

        # Create context with current usage
        current_usage = await self.get_current_usage(tenant_id)

        context = TenantContext(
            tenant_id=tenant_id,
            tier=tenant_config.tier,
            limits=tenant_config.limits,
            current_usage=current_usage,
            permissions=tenant_config.permissions
        )

        # Cache context
        await self.cache.set(cache_key, context, ttl=300)  # 5 minute cache

        return context

    async def enforce_rate_limits(
        self,
        tenant_id: str,
        operation: str,
        context: TenantContext
    ) -> bool:
        """
        Enforce rate limiting based on tenant tier and current usage.

        Uses sliding window rate limiting with Redis for
        accurate distributed rate limiting.
        """

        limit_key = f"rate_limit:{tenant_id}:{operation}"
        window_seconds = 60  # 1 minute window

        # Get operation-specific limits
        operation_limits = context.limits.get(operation, {})
        requests_per_minute = operation_limits.get('requests_per_minute', 100)

        # Sliding window rate limiting using Redis
        current_time = int(time.time())
        window_start = current_time - window_seconds

        # Remove expired entries
        await self.cache.redis.zremrangebyscore(limit_key, 0, window_start)

        # Count current requests in window
        current_count = await self.cache.redis.zcard(limit_key)

        if current_count >= requests_per_minute:
            # Rate limit exceeded
            retry_after = await self.calculate_retry_after(limit_key, window_seconds)
            raise RateLimitError(
                f"Rate limit exceeded: {current_count}/{requests_per_minute} per minute",
                retry_after=retry_after
            )

        # Add current request to window
        await self.cache.redis.zadd(limit_key, {str(current_time): current_time})
        await self.cache.redis.expire(limit_key, window_seconds + 10)  # Cleanup buffer

        return True

    async def check_storage_quota(
        self,
        tenant_id: str,
        additional_content_size: int,
        context: TenantContext
    ) -> bool:
        """Check if tenant can store additional content within quota."""

        storage_limit = context.limits.get('max_storage_mb', 1000)  # Default 1GB
        current_storage = context.current_usage.get('storage_mb', 0)

        additional_mb = additional_content_size / (1024 * 1024)

        if current_storage + additional_mb > storage_limit:
            raise QuotaExceededError(
                f"Storage quota exceeded: {current_storage + additional_mb:.2f}MB / {storage_limit}MB"
            )

        return True
```

### Security and Compliance

**Data Security**:
```python
class SecurityManager:
    """
    Manages data security, encryption, and compliance requirements.

    Features:
    - Content encryption at rest and in transit
    - PII detection and redaction
    - Audit logging for compliance
    - Access control and permissions
    """

    def __init__(self, encryption_key: str, audit_logger: AuditLogger):
        self.cipher = Fernet(encryption_key.encode())
        self.audit_logger = audit_logger
        self.pii_detector = PIIDetector()

    async def secure_content_storage(
        self,
        content: str,
        metadata: dict,
        tenant_id: str,
        user_id: str
    ) -> SecureContent:
        """
        Secure content before storage with encryption and PII handling.

        Process:
        1. Detect and handle PII in content
        2. Encrypt sensitive data fields
        3. Generate audit trail
        4. Return secured content for storage
        """

        # Detect PII in content
        pii_findings = await self.pii_detector.scan_content(content)

        # Handle PII based on tenant policy
        processed_content, redaction_map = await self.handle_pii(
            content, pii_findings, tenant_id
        )

        # Encrypt sensitive metadata fields
        secure_metadata = await self.encrypt_sensitive_metadata(metadata)

        # Generate audit log entry
        audit_entry = AuditEntry(
            tenant_id=tenant_id,
            user_id=user_id,
            action="content_storage",
            content_hash=self.hash_content(processed_content),
            pii_detected=len(pii_findings) > 0,
            encryption_applied=True,
            timestamp=datetime.utcnow()
        )

        await self.audit_logger.log_entry(audit_entry)

        return SecureContent(
            content=processed_content,
            metadata=secure_metadata,
            redaction_map=redaction_map,
            audit_id=audit_entry.id
        )

    async def handle_pii(
        self,
        content: str,
        pii_findings: List[PIIFinding],
        tenant_id: str
    ) -> Tuple[str, dict]:
        """
        Handle PII based on tenant data policy.

        Options:
        - Redact: Replace with placeholder tokens
        - Encrypt: Encrypt in place with tenant key
        - Remove: Delete PII sections entirely
        - Preserve: Keep with additional audit logging
        """

        tenant_policy = await self.get_tenant_pii_policy(tenant_id)
        redaction_map = {}
        processed_content = content

        for finding in sorted(pii_findings, key=lambda f: f.start, reverse=True):
            # Process from end to start to preserve indices
            pii_text = content[finding.start:finding.end]

            if tenant_policy.pii_handling == "redact":
                replacement = f"[{finding.pii_type.upper()}_REDACTED]"
                processed_content = (
                    processed_content[:finding.start] +
                    replacement +
                    processed_content[finding.end:]
                )
                redaction_map[finding.id] = {
                    "original_text": self.cipher.encrypt(pii_text.encode()).decode(),
                    "replacement": replacement,
                    "pii_type": finding.pii_type
                }

            elif tenant_policy.pii_handling == "encrypt":
                encrypted_text = self.cipher.encrypt(pii_text.encode()).decode()
                processed_content = (
                    processed_content[:finding.start] +
                    f"[ENCRYPTED:{encrypted_text}]" +
                    processed_content[finding.end:]
                )

            elif tenant_policy.pii_handling == "remove":
                processed_content = (
                    processed_content[:finding.start] +
                    processed_content[finding.end:]
                )
                redaction_map[finding.id] = {
                    "removed_text": self.cipher.encrypt(pii_text.encode()).decode(),
                    "pii_type": finding.pii_type
                }

        return processed_content, redaction_map
```

## Learning Algorithm Diagnostics

SomaBrain’s adaptation engine lives in `somabrain/learning/adaptation.py`. It implements decoupled, per‑parameter updates with configurable gains and constraints, and optional neuromodulated learning rates. Earlier internal notes about “coupled parameters” are outdated.

### Decoupled Parameter Updates

```python
def apply_feedback(self, utility: float, reward: Optional[float] = None) -> bool:
    signal = reward if reward is not None else utility
    # Dynamic or signal‑scaled LR
    self._lr = (
        self._base_lr * min(max(0.5 + self._get_dopamine_level(), 0.5), 1.2)
        if self._enable_dynamic_lr
        else self._base_lr * (1.0 + float(signal))
    )

    semantic_signal = float(signal)
    utility_signal = float(reward) if reward is not None else semantic_signal
    # Independent deltas via AdaptationGains
    self._retrieval.alpha = self._constrain(
        "alpha", self._retrieval.alpha + self._lr * self._gains.alpha * semantic_signal
    )
    self._retrieval.gamma = self._constrain(
        "gamma", self._retrieval.gamma + self._lr * self._gains.gamma * semantic_signal
    )
    self._utility.lambda_ = self._constrain(
        "lambda_", self._utility.lambda_ + self._lr * self._gains.lambda_ * utility_signal
    )
    self._utility.mu = self._constrain(
        "mu", self._utility.mu + self._lr * self._gains.mu * utility_signal
    )
    self._utility.nu = self._constrain(
        "nu", self._utility.nu + self._lr * self._gains.nu * utility_signal
    )
    return True
```

- Alpha and lambda_ often increase together under positive utility, but they are not coupled or forced to be identical—each has its own gain and may be driven by distinct signals.
- Gamma has a negative default gain and is bounded in [0, 1], so it typically decreases under positive utility until constrained.
- The effective learning rate can be driven by the dopamine neuromodulator if enabled.

### Evidence from Telemetry and Tests

| Observation | Source |
| --- | --- |
| Directional updates (alpha/lambda_ increase; gamma non‑increasing) | `tests/workflow/test_adaptation_cycle.py` |
| Env overrides for gains and bounds respected | `tests/workflow/test_adaptation_cycle.py` |
| State persists per tenant with TTL | `somabrain/learning/adaptation.py` (Redis setex) |

### Summary

- The engine performs genuine adaptation with independent channels and guardrails.
- Infrastructure (Redis, metrics) is production‑ready; documentation now reflects the decoupled design.

### Adjacent Improvements (optional)

1. Expose per‑parameter delta metrics for richer introspection.
2. Feed more explicit semantic/utility signals where available.
3. Add property tests for decorrelation when reward ≠ utility.

## Mathematical Appendices

### Density Matrix Maintenance

`somabrain/memory/density.py` maintains the ρ matrix used by the unified scorer. Keep code and math synchronized.

- Representation: ρ is a real symmetric matrix with shape `(dim, dim)`.
- Updates: `DensityMatrix.observe(vec, alpha)` normalizes `vec`, applies the rank-1 update `ρ' = (1 - alpha) * ρ + alpha * (v vᵀ)`, then reprojects.
- Projection steps:
    1. Trace normalization via `normalize_trace()` so `trace(ρ) = 1`.
    2. PSD projection via `project_psd()` to clip negative eigenvalues.
    3. Symmetrization with `(ρ + ρᵀ) / 2` to counter floating point drift.
- Metrics: `somabrain_density_trace_error_total`, `somabrain_density_psd_clip_total`, `somabrain_density_condition_number`.
- Tests: `tests/test_fd_salience.py`, `tests/test_unified_scorer.py`, and `tests/test_legacy_purge.py` guard PSD, weight bounds, and stub regressions.

### BHDC Binding Cheat Sheet

`somabrain/quantum.py` implements binary hyperdimensional computing (BHDC). Key reminders:

- Hypervector construction: dimension from `HRRConfig.dim` (default 2048); RNG seeded with `HRRConfig.seed`; sparsity controls ones vs minus ones.
- Role generation: `QuantumLayer.make_unitary_role(role)` hashes the role, seeds a temporary RNG, and produces a permutation vector that is its own inverse.
- Binding & unbinding: `bind_unitary(vec, role)` performs circular convolution; `unbind_unitary(bound, role)` applies the conjugate to reverse the operation.
- Superposition & cleanup: `superpose` averages bound vectors and renormalizes to ±1; `cleanup` selects the stored vector with maximum cosine similarity.
- Tests: `tests/test_bhdc_binding.py` checks bind/unbind symmetry; `benchmarks/numerics_bench.py` validates numerical stability.

**Verification**: Domain knowledge is comprehensive when you understand the mathematical foundations, can explain architectural decisions, and can implement new cognitive features.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Vector dimension mismatch | Ensure consistent model usage across encoding/storage |
| Poor similarity results | Check text preprocessing and vector normalization |
| Slow database queries | Optimize indexes and query structure |
| Memory usage spikes | Implement batch processing and connection pooling |
| Tenant data leakage | Verify all queries include tenant_id filtering |

**References**:
- [Codebase Walkthrough](codebase-walkthrough.md) for implementation details
- [First Contribution](first-contribution.md) for hands-on practice
- [Technical Manual](../technical/index.md) for operational knowledge
- [API Reference](../development/api-reference.md) for integration patterns# Onboarding Manual

**Purpose**: This manual helps agent coders, new developers, contractors, and team members quickly become productive on SomaBrain.

**Audience**: New team members, agent coders, contractors, and anyone joining the SomaBrain project.

**Prerequisites**: Basic programming knowledge; specific technology experience will be covered in setup guides.

---

## Welcome to SomaBrain! 🧠

This guide will take you from zero to productive contributor in the SomaBrain cognitive memory platform.

## Quick Navigation

- [Project Context](project-context.md) - Mission, goals, and business context
- [Codebase Walkthrough](codebase-walkthrough.md) - Repository tour and architecture patterns
- [First Contribution](first-contribution.md) - Complete walkthrough for your first PR
- [Team Collaboration](team-collaboration.md) - Communication channels and processes
- [Domain Knowledge](domain-knowledge.md) - Technical deep-dive and business logic

---

## Your First Week Plan

### Day 1-2: Context & Setup
1. Read [Project Context](project-context.md) to understand what SomaBrain does
2. Follow [Local Setup](../development/local-setup.md) to get your development environment running
3. Verify your setup works by running tests

### Day 3-4: Code Exploration
1. Work through [Codebase Walkthrough](codebase-walkthrough.md) to understand the architecture
2. Read [Domain Knowledge](domain-knowledge.md) for technical depth
3. Review [Team Collaboration](team-collaboration.md) to understand our processes

### Day 5: First Contribution
1. Follow [First Contribution](first-contribution.md) guide to make your first PR
2. Review [Contribution Process](../development/contribution-process.md) before submitting
3. Celebrate! 🎉

## Getting Help

Stuck on something? Here's how to get help:

1. **Check [FAQ](../user/faq.md)** for common issues
2. **Search [Glossary](../glossary.md)** for unfamiliar terms
3. **Ask in team channels** (see [Team Collaboration](team-collaboration.md))
4. **Open a documentation issue** if something is unclear

## Project Fundamentals

**What SomaBrain Does**: Cognitive memory platform using hyperdimensional computing for semantic storage and reasoning

**Core Principles**:
- **Mathematical Truth**: No mocking, no fake data - only real mathematical operations
- **Strict Mode**: Production code paths require real backing services
- **Observable**: Comprehensive metrics and audit trails
- **Scalable**: Multi-tenant architecture supporting millions of operations

---

**Verification**: Complete your first contribution before considering onboarding finished.

**Common Errors**: See [FAQ](../user/faq.md) for setup and development issues.

**References**:
- [Development Manual](../development/index.md) for detailed technical guides
- [User Manual](../user/index.md) to understand user experience
- [Technical Manual](../technical/index.md) for operational context# Codebase Walkthrough

**Purpose**: Comprehensive tour of the SomaBrain codebase architecture, component relationships, and development patterns to help new developers understand the system quickly.

**Audience**: New developers, agent coders, and contributors joining the SomaBrain project.

**Prerequisites**: Basic understanding of Python, FastAPI, and modern web development. Completed [Local Setup](../development/local-setup.md).

---

## Repository Structure Overview

```
somabrain/
├── somabrain/           # Main application package
│   ├── api/            # FastAPI application and routes
│   ├── core/           # Business logic and cognitive operations
│   ├── database/       # Database models and connections
│   ├── models/         # Pydantic data models
│   ├── services/       # External service integrations
│   └── utils/          # Shared utilities and helpers
├── tests/              # Test suite (unit, integration, e2e)
├── migrations/         # Database schema migrations (Alembic)
├── benchmarks/         # Performance benchmarks and profiling
├── docs/              # Documentation (this manual)
├── scripts/           # Development and deployment scripts
├── config/            # Configuration templates and examples
└── docker/            # Docker configurations and compose files
```

### Key Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project configuration, dependencies, build settings |
| `docker-compose.yml` | Local development environment setup |
| `alembic.ini` | Database migration configuration |
| `Makefile` | Common development commands and shortcuts |
| `.github/workflows/` | CI/CD pipeline definitions |

---

## Core Application Architecture

### High-Level System Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Python SDK    │    │  TypeScript SDK │
│   (Browser)     │    │   (Library)     │    │   (Library)     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │       FastAPI Server      │
                    │    (Port 9696)           │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
    ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
    │ PostgreSQL│         │   Redis   │         │  Vector   │
    │ Database  │         │   Cache   │         │ Service   │
    │(Port 5432)│         │(Port 6379)│         │ (Qdrant)  │
    └───────────┘         └───────────┘         └───────────┘
```

### Application Layers

**API Layer** (`somabrain/api/`):
- HTTP endpoints and request/response handling
- Authentication and authorization middleware
- Input validation and serialization
- Error handling and logging

**Core Layer** (`somabrain/core/`):
- Business logic implementation
- Cognitive reasoning algorithms
- Memory management operations
- Vector encoding and similarity computation

**Data Layer** (`somabrain/database/`):
- Database models and schemas
- Query optimization and indexes
- Connection pooling and transactions
- Data access patterns

---

## Key Components Deep Dive

### 1. Memory Manager (`somabrain/core/memory_manager.py`)

**Purpose**: Central component for all memory operations - storage, retrieval, and reasoning.

```python
class MemoryManager:
    """
    Core memory operations manager.

    Handles the complete lifecycle of memories:
    - Encoding content to vectors using transformer models
    - Storing memories with metadata in PostgreSQL
    - Performing semantic similarity searches
    - Managing tenant isolation and security
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.vector_encoder = VectorEncoder(config.model_name)
        self.database = DatabaseManager(config.database_url)
        self.cache = CacheManager(config.redis_url)

    async def store_memory(
        self,
        content: str,
        metadata: dict,
        tenant_id: str
    ) -> str:
        """Store new memory with vector encoding."""

    async def recall_memories(
        self,
        query: str,
        k: int = 10,
        tenant_id: str
    ) -> List[Memory]:
        """Retrieve semantically similar memories."""
```

**Key Methods**:
- `store_memory()`: Encodes and stores new memories
- `recall_memories()`: Semantic similarity search
- `update_memory()`: Updates existing memory content
- `delete_memory()`: Removes memories (with audit trail)
- `analyze_patterns()`: Discovers memory patterns and relationships

### 2. Vector Encoder (`somabrain/core/vector_encoder.py`)

**Purpose**: Converts text content into high-dimensional vector representations for semantic similarity.

```python
class VectorEncoder:
    """
    Handles text-to-vector encoding using transformer models.

    Uses sentence-transformers library with models like:
    - all-MiniLM-L6-v2 (384 dimensions, fast)
    - all-mpnet-base-v2 (768 dimensions, accurate)
    """

    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        """Convert text to vector representation."""

    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between vectors."""
```

**Performance Considerations**:
- Model loading is expensive - singleton pattern used
- Batch encoding for multiple texts
- GPU acceleration when available
- Vector normalization for consistent similarity scores

### 3. Database Layer (`somabrain/database/`)

**Core Models** (`models.py`):
```python
class Memory(Base):
    """
    Main memory storage table.

    Stores content, metadata, vector encodings, and audit information.
    Partitioned by tenant_id for isolation and performance.
    """
    __tablename__ = "memories"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=False)
    vector_encoding = Column(ARRAY(Float), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index('ix_memories_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_memories_tenant_metadata', 'tenant_id', 'metadata', postgresql_using='gin'),
    )

class Tenant(Base):
    """Tenant configuration and limits."""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    settings = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Database Manager** (`connection.py`):
```python
class DatabaseManager:
    """
    Handles all database operations with connection pooling.

    Features:
    - Async PostgreSQL operations using asyncpg
    - Connection pooling for performance
    - Transaction management
    - Query optimization and explain plans
    """

    async def store_memory(self, memory: Memory) -> str:
        """Store memory with vector in single transaction."""

    async def search_memories(
        self,
        query_vector: np.ndarray,
        tenant_id: str,
        limit: int = 10,
        threshold: float = 0.2
    ) -> List[Memory]:
        """Vector similarity search with pgvector."""
```

### 4. API Layer (`somabrain/api/`)

**Main Application** (`main.py`):
```python
def create_app(config: AppConfig) -> FastAPI:
    """
    FastAPI application factory.

    Sets up:
    - CORS middleware for web clients
    - Authentication middleware
    - Prometheus metrics collection
    - Request/response logging
    - Error handlers
    """
    app = FastAPI(
        title="SomaBrain API",
        description="Cognitive Memory Platform",
        version=__version__
    )

    # Middleware setup
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(AuthenticationMiddleware, ...)
    app.add_middleware(PrometheusMiddleware, ...)

    # Router registration
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(reasoning_router, prefix="/api/v1")
    app.include_router(tenant_router, prefix="/api/v1")

    return app
```

**Route Handlers** (`routers/memory.py`):
```python
@router.post("/remember", response_model=MemoryResponse)
async def store_memory(
    request: MemoryRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Store a new memory.

    1. Validate request content and metadata
    2. Check tenant limits and quotas
    3. Encode content to vector representation
    4. Store in database with audit trail
    5. Return memory ID and metadata
    """

@router.post("/recall", response_model=RecallResponse)
async def recall_memories(
    request: RecallRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Search for semantically similar memories.

    1. Validate query and parameters
    2. Encode query to vector
    3. Perform similarity search in database
    4. Apply metadata filters
    5. Return ranked results with scores
    """
```

---

## Data Flow Patterns

### Memory Storage Flow

```mermaid
graph TD
    A[Client Request] --> B[API Validation]
    B --> C[Authentication Check]
    C --> D[Tenant Validation]
    D --> E[Content Encoding]
    E --> F[Vector Generation]
    F --> G[Database Transaction]
    G --> H[Audit Logging]
    H --> I[Cache Update]
    I --> J[Response Return]
```

**Detailed Steps**:
1. **Request Validation**: Check content length, metadata format
2. **Authentication**: Verify API key and permissions
3. **Tenant Check**: Validate tenant exists and within limits
4. **Content Processing**: Clean and prepare text for encoding
5. **Vector Encoding**: Convert text to numerical representation
6. **Database Storage**: Store in PostgreSQL with ACID guarantees
7. **Audit Trail**: Log operation for compliance and debugging
8. **Cache Operations**: Update Redis cache for performance
9. **Response**: Return memory ID and confirmation

### Memory Recall Flow

```mermaid
graph TD
    A[Search Query] --> B[Query Encoding]
    B --> C[Vector Search]
    C --> D[Similarity Scoring]
    D --> E[Metadata Filtering]
    E --> F[Ranking & Sorting]
    F --> G[Result Formatting]
    G --> H[Response Return]
```

**Performance Optimizations**:
- **Batch Vector Operations**: Process multiple queries together
- **Database Indexing**: pgvector indexes for fast similarity search
- **Result Caching**: Cache frequent queries in Redis
- **Lazy Loading**: Only fetch full content when needed

---

## Configuration Management

### Application Configuration (`somabrain/config.py`)

```python
class AppConfig(BaseSettings):
    """
    Application configuration with environment variable support.

    Supports multiple environments (dev, staging, prod) with
    appropriate defaults and validation.
    """

    # Database
    database_url: str = "postgresql://user:pass@localhost/somabrain"
    database_pool_size: int = 10

    # Vector Service
    vector_model: str = "all-MiniLM-L6-v2"
    vector_dimensions: int = 384

    # Redis Cache
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600

    # API Settings
    api_key_header: str = "X-API-Key"
    tenant_id_header: str = "X-Tenant-ID"
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60

    # Monitoring
    prometheus_metrics: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = "SOMABRAIN_"
```

### Environment-Specific Configs

**Development** (`.env.development`):
```bash
SOMABRAIN_DATABASE_URL=postgresql://dev:dev@localhost/somabrain_dev
SOMABRAIN_LOG_LEVEL=DEBUG
SOMABRAIN_PROMETHEUS_METRICS=false
```

**Production** (`.env.production`):
```bash
SOMABRAIN_DATABASE_URL=postgresql://prod_user:${DB_PASSWORD}@db.prod/somabrain
SOMABRAIN_LOG_LEVEL=WARNING
SOMABRAIN_PROMETHEUS_METRICS=true
```

---

## Testing Architecture

### Test Structure

```
tests/
├── unit/               # Fast, isolated component tests
│   ├── core/          # Memory manager, encoding logic
│   ├── api/           # Route handlers, validation
│   ├── database/      # Model tests, query logic
│   └── utils/         # Helper function tests
├── integration/        # Component interaction tests
│   ├── api/           # End-to-end API workflows
│   ├── database/      # Database integration patterns
│   └── services/      # External service integration/adapters
├── e2e/               # Full system tests
│   ├── user_workflows/ # Complete user scenarios
│   ├── performance/   # Load and stress testing
│   └── deployment/    # Docker and infrastructure tests
└── fixtures/          # Shared test data and utilities
```

### Test Patterns

**Unit Test Example**:
```python
# tests/unit/core/test_memory_manager.py
@pytest.mark.asyncio
async def test_store_memory_success():
    """Test successful memory storage with all components mocked."""

    # Arrange - Mock all dependencies
    mock_encoder = Mock()
    mock_encoder.encode.return_value = np.array([1, 2, 3])

    mock_db = AsyncMock()
    mock_db.store_memory.return_value = "mem_123"

    manager = MemoryManager(encoder=mock_encoder, database=mock_db)

    # Act - Call method under test
    result = await manager.store_memory(
        content="Test content",
        metadata={"category": "test"},
        tenant_id="test_tenant"
    )

    # Assert - Verify behavior
    assert result == "mem_123"
    mock_encoder.encode.assert_called_once_with("Test content")
    mock_db.store_memory.assert_called_once()
```

**Integration Test Example**:
```python
# tests/integration/api/test_memory_endpoints.py
@pytest.mark.asyncio
async def test_store_and_recall_workflow():
    """Test complete memory storage and retrieval via API."""

    # Uses real database, real encoder, but isolated test tenant
    async with AsyncClient(app=app, base_url="http://test") as client:

        # Store memory
        store_response = await client.post("/remember", json={
            "content": "Integration test content",
            "metadata": {"type": "integration_test"}
        }, headers={"X-Tenant-ID": "test_tenant"})

        memory_id = store_response.json()["memory_id"]

        # Recall memory
        recall_response = await client.post("/recall", json={
            "query": "integration test",
            "k": 5
        }, headers={"X-Tenant-ID": "test_tenant"})

        results = recall_response.json()["results"]

        # Verify end-to-end workflow
        assert len(results) > 0
        assert any(r["memory_id"] == memory_id for r in results)
```

---

## Development Patterns

### Dependency Injection

**FastAPI Dependencies**:
```python
# somabrain/api/dependencies.py
async def get_database_manager() -> DatabaseManager:
    """Provide database manager instance."""
    return database_manager_instance

async def get_memory_manager(
    db: DatabaseManager = Depends(get_database_manager)
) -> MemoryManager:
    """Provide memory manager with injected dependencies."""
    return MemoryManager(database=db, encoder=vector_encoder)

async def get_current_tenant(
    request: Request,
    api_key: str = Header(..., alias="X-API-Key")
) -> str:
    """Extract and validate tenant from headers."""
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(400, "Missing tenant ID")
    return tenant_id
```

### Error Handling Patterns

**Custom Exception Hierarchy**:
```python
# somabrain/exceptions.py
class SomaBrainError(Exception):
    """Base exception for all SomaBrain errors."""
    pass

class ValidationError(SomaBrainError):
    """Request validation errors."""
    pass

class AuthenticationError(SomaBrainError):
    """Authentication and authorization errors."""
    pass

class MemoryNotFoundError(SomaBrainError):
    """Memory lookup errors."""
    pass

class EncodingError(SomaBrainError):
    """Vector encoding failures."""
    pass
```

**Error Handler Middleware**:
```python
@app.exception_handler(SomaBrainError)
async def somabrain_exception_handler(request: Request, exc: SomaBrainError):
    """Convert application errors to proper HTTP responses."""

    error_mapping = {
        ValidationError: 400,
        AuthenticationError: 401,
        MemoryNotFoundError: 404,
        EncodingError: 500
    }

    status_code = error_mapping.get(type(exc), 500)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "request_id": request.state.request_id
            }
        }
    )
```

### Async Patterns

**Database Operations**:
```python
async def process_batch_memories(memories: List[Dict]) -> List[str]:
    """Process multiple memories concurrently."""

    async def process_single_memory(memory_data):
        async with database.transaction():
            # Encode vector
            vector = await encoder.encode(memory_data["content"])

            # Store in database
            memory_id = await database.store_memory(
                content=memory_data["content"],
                metadata=memory_data["metadata"],
                vector=vector
            )

            return memory_id

    # Process all memories concurrently
    tasks = [process_single_memory(mem) for mem in memories]
    return await asyncio.gather(*tasks)
```

---

## Performance Patterns

### Caching Strategy

**Multi-Level Caching**:
```python
class CacheManager:
    """
    Multi-level caching for performance optimization.

    L1: In-memory LRU cache for frequent vectors
    L2: Redis cache for computed results
    L3: Database with optimized indexes
    """

    def __init__(self):
        self.memory_cache = LRUCache(maxsize=1000)  # L1
        self.redis_client = Redis()                  # L2

    async def get_similar_memories(self, query_vector, tenant_id):
        # L1: Check in-memory cache
        cache_key = f"similar:{tenant_id}:{hash(query_vector.tobytes())}"

        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # L2: Check Redis cache
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            self.memory_cache[cache_key] = result
            return result

        # L3: Database query
        result = await self.database.search_memories(query_vector, tenant_id)

        # Populate caches
        await self.redis_client.setex(cache_key, 3600, json.dumps(result))
        self.memory_cache[cache_key] = result

        return result
```

### Database Optimization

**Query Patterns**:
```sql
-- Optimized similarity search with pgvector
SELECT
    id, content, metadata,
    1 - (vector_encoding <=> %s) AS similarity_score
FROM memories
WHERE
    tenant_id = %s
    AND 1 - (vector_encoding <=> %s) > %s  -- threshold filter
ORDER BY vector_encoding <=> %s  -- pgvector distance operator
LIMIT %s;

-- Metadata filtering with GIN indexes
SELECT id, content
FROM memories
WHERE
    tenant_id = %s
    AND metadata @> %s  -- JSON contains operator
ORDER BY created_at DESC;
```

**Connection Pooling**:
```python
class DatabasePool:
    """Connection pool for high-concurrency database access."""

    def __init__(self, database_url: str, pool_size: int = 20):
        self.pool = asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=pool_size,
            command_timeout=30
        )

    async def execute_query(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
```

**Verification**: Codebase understanding is complete when you can navigate the architecture, understand component relationships, and identify where to make changes for new features.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Import errors | Check PYTHONPATH and virtual environment |
| Database connection fails | Verify PostgreSQL is running and accessible |
| Vector encoding slow | Use GPU acceleration or smaller models |
| Tests fail intermittently | Check for async race conditions and proper cleanup |

**References**:
- [Local Setup](../development/local-setup.md) for development configuration
- [Domain Knowledge](domain-knowledge.md) for deep technical understanding
- [First Contribution](first-contribution.md) for hands-on practice
- [Development Manual](../development/index.md) for detailed technical guides# First Contribution

**Purpose**: Complete walkthrough for making your first code contribution to SomaBrain, from issue selection to pull request merge.

**Audience**: New contributors, developers making their first SomaBrain contribution, and team members learning the workflow.

**Prerequisites**: Completed [Local Setup](../development/local-setup.md) and read [Codebase Walkthrough](codebase-walkthrough.md).

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

**Add Examples to API Reference** (`docs/development/api-reference.md`):
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

**Add to Memory Operations Guide** (`docs/user/memory-operations.md`):
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
- [Local Setup](../development/local-setup.md) for development environment
- [Development Manual](../development/contribution-process.md) for detailed process
- [Contribution Process](../development/contribution-process.md) before submitting pull requests