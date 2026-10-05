# A2A file templates

## Handoff header (SOMA-BR-COORD-A2A-001)

```markdown
| Field | Value |
|---|---|
| Document Identifier | SOMA-BR-COORD-A2A-001 |
| From | <agent-id> |
| To | <other-agent> |
| Branch | <working-branch> |
| Channel | docs/plans/a2a/ |
```

## Ledger row

`| ISO timestamp | agent-id | ACTION | detail |`

Actions: OPEN, ACK, COMMIT, BRANCH, WAVE, CLAIM, RELEASE, CONFLICT, MERGE

## Claim row

`| path/prefix | agent-id | task-id | ISO timestamp | ACTIVE|RELEASED|DONE |`

## Inbox message

```markdown
## [ISO timestamp] FROM <me> TO <them>

<body>
```
