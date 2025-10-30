# Quick Reference - Multi-Agent System

## Starting
```bash
cd /app/exercs/09-agent
python main.py
```

## Talking to Team Members

### Direct Address Format
```
[Leader]: <Agent Name>, <your message>
```

### Agent Keywords
| Agent | Keywords | Role |
|-------|----------|------|
| **Secretary** | `secretary`, `sec` | Admin, coordination, research |
| **CTO** | `cto`, `chief technology officer` | Technical strategy, architecture |
| **Lead Developer** | `lead developer`, `lead dev`, `developer` | Implementation, coding |
| **QA Lead** | `qa lead`, `qa`, `quality assurance` | Testing, quality |

### Examples
```
[Leader]: Secretary, ask everyone for their roles
[Leader]: CTO, what's the best database for our use case?
[Leader]: Lead Dev, implement user authentication
[Leader]: QA, what testing tools should we use?
[Leader]: What's the project status?  ← defaults to Secretary
```

## Commands
- **quit** / **exit** / **q** - End session and save logs

## Features

### 🧠 Memory
- All agents remember previous conversations
- Can reference past decisions and information
- Example: "Who is the CTO?" → Agent recalls from previous broadcast

### 📝 Logging
- All interactions logged to `conversation_log.jsonl`
- View logs: `cat conversation_log.jsonl | jq`

### 🔄 Loop Mode
- Continuous operation - no need to restart
- Each interaction builds on previous knowledge

### 📡 Broadcast
- Agents can ask ALL team members for input simultaneously
- Responses collected in parallel
- Example: Secretary broadcasts "roles request" → all respond at once

### 🤝 Delegation
- Agents can delegate tasks to specific colleagues
- Example: Secretary → CTO for technical questions

### 🔍 Web Search
- Agents can search the web for information
- Example: "What are the latest Python testing frameworks?"

### 🤖 LLM Integration
- Agents can use LLM for analysis and generation
- Custom prompts for specific tasks

## Workflow
```
┌─────────────────┐
│  User Input     │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Parse   │ ← Detects which agent to route to
    │  Agent   │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │ Agent Decides │ ← search/llm/broadcast/delegate/answer
    └────┬──────────┘
         │
    ┌────▼────────┐
    │   Action    │ ← Execute chosen action
    └────┬────────┘
         │
    ┌────▼─────────┐
    │ Display      │
    │ Result       │
    └────┬─────────┘
         │
    └────▼─────────┐
         Loop Back  │ ← Ready for next input
    ─────────────┘
```

## Tips

1. **Be specific**: "CTO, evaluate React vs Vue" works better than "Should we use React?"

2. **Use broadcast for consensus**: "Secretary, ask everyone about the project timeline"

3. **Build on context**: Agents remember, so you can ask follow-up questions

4. **Check logs**: All decisions and reasoning are logged for transparency

5. **Default to Secretary**: For general coordination tasks, just ask directly

## Log Analysis

```bash
# View all logs
cat conversation_log.jsonl | jq

# Recent 10 entries
tail -10 conversation_log.jsonl | jq

# Filter by agent
cat conversation_log.jsonl | jq 'select(.agent == "cto")'

# Filter by type
cat conversation_log.jsonl | jq 'select(.type == "decision")'

# Count interactions
cat conversation_log.jsonl | wc -l
```
