# Multi-Agent Communication Guide

## Overview

You can now communicate with **one or multiple team members simultaneously** using two different syntaxes.

## Syntax Options

### 1. Single Agent (Direct Address)
Start your message with the agent's name:
```
[Leader]: <Agent Name>, <message>
```

**Examples:**
```
[Leader]: Secretary, coordinate the meeting
[Leader]: CTO, review the architecture
[Leader]: Lead Developer, fix the bug in auth.py
[Leader]: QA Lead, what's the test coverage?
```

### 2. Multiple Agents (@mentions)
Use `@` mentions to address multiple agents:
```
[Leader]: @<Agent1> @<Agent2> <message>
```

**Examples:**
```
[Leader]: @CTO @Dev review the API design
[Leader]: @QA @Dev discuss test automation
[Leader]: @CTO @QA @Dev thoughts on the release?
```

## Agent Name Mappings

| Full Name | Direct Keywords | @mention Keywords |
|-----------|----------------|-------------------|
| **Secretary** | `secretary`, `sec` | `@secretary`, `@sec` |
| **CTO** | `cto`, `chief technology officer` | `@cto` |
| **Lead Developer** | `lead developer`, `lead dev`, `developer` | `@dev`, `@developer`, `@lead_dev`, `@lead_developer` |
| **QA Lead** | `qa lead`, `qa`, `quality assurance` | `@qa`, `@qa_lead`, `@quality_assurance` |

## How Multi-Agent Works

### Processing Flow
```
User: "@CTO @Dev review the authentication design"
  ↓
Parse @mentions → [CTO, Dev]
  ↓
Send to TargetedBroadcastNode
  ↓
Both agents receive message IN PARALLEL
  ↓          ↓
CTO processes    Dev processes
  ↓          ↓
Both respond with their analysis
  ↓
Responses compiled and displayed together
```

### Key Features

1. **Parallel Processing**: All mentioned agents respond simultaneously (AsyncParallelBatchNode)
2. **Independent Responses**: Each agent uses their own role/expertise
3. **Compiled Output**: All responses shown together for easy comparison
4. **Direct Routing**: Bypasses decision-making - agents respond immediately

## Use Cases

### Collaborative Review
```
[Leader]: @CTO @Dev @QA evaluate this new feature proposal
```
Get architectural, implementation, and quality perspectives at once.

### Cross-Functional Discussion
```
[Leader]: @Dev @QA what's blocking the release?
```
Understand blockers from both development and testing sides.

### Technical Consensus
```
[Leader]: @CTO @Dev which framework should we use for the frontend?
```
Get aligned technical opinions from leadership and implementation.

### Status Update
```
[Leader]: @CTO @Dev @QA @Secretary status update on Project X
```
Get comprehensive status from all team members simultaneously.

## Comparison: Single vs Multi vs Broadcast

| Method | Syntax | Agents | Processing | Use When |
|--------|--------|--------|------------|----------|
| **Single** | `CTO, message` | 1 specific | Sequential decision-making | Need one expert's help |
| **Multi** | `@CTO @Dev message` | 2-3 specific | Parallel responses | Need specific experts' input |
| **Broadcast** | Via agent: "ask everyone" | All 4 | Parallel responses | Need everyone's input |

## Examples in Action

### Example 1: Design Review
```
[Leader]: @CTO @Dev review the microservices architecture for the payment system

[CTO] Response:
From an architectural perspective, the microservices approach is sound for the payment system...
[detailed technical review]

[LEAD_DEVELOPER] Response:
Implementation-wise, I recommend using REST APIs between services...
[detailed implementation view]

============================================================
Responses from 2 team members compiled above.
```

### Example 2: Release Planning
```
[Leader]: @Dev @QA are we ready for the v2.0 release?

[LEAD_DEVELOPER] Response:
From development side, all features are complete. Minor bug fixes remain...

[QA_LEAD] Response:
QA perspective: 95% test coverage achieved. Two critical bugs need fixing...

============================================================
```

### Example 3: Technology Decision
```
[Leader]: @CTO @Dev PostgreSQL vs MongoDB for our use case?

[Both analyze and respond with their perspectives]
[You get both architectural and practical implementation views]
```

## Tips

1. **Be Specific**: "@CTO @Dev" is better than just asking everyone
2. **Use for Decisions**: Great for getting multiple perspectives on technical choices
3. **Combine with Follow-ups**: After multi-agent response, follow up with specific agent if needed
4. **Memory Enabled**: All agents remember the multi-agent discussion in future interactions

## Technical Implementation

This feature uses PocketFlow's `AsyncParallelBatchNode`:
- Each agent processed as a separate async task
- All tasks execute concurrently
- Results collected and compiled
- Direct path: Input → TargetedBroadcast → Display (no intermediate decisions)

## Logging

All multi-agent interactions are logged:
```json
{"type": "targeted_broadcast", "agent": "user", "content": "To cto, lead_developer"}
{"type": "targeted_broadcast_response", "agent": "cto", "content": "..."}
{"type": "targeted_broadcast_response", "agent": "lead_developer", "content": "..."}
```

View in logs:
```bash
cat conversation_log.jsonl | jq 'select(.type == "targeted_broadcast")'
```
