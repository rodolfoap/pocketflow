# Developer Guide: Multi-Agent System

> A narrative guide to understanding and extending this PocketFlow-based multi-agent system

## What This System Does

Imagine you're leading a software team with 4 employees: a Secretary, CTO, Lead Developer, and QA Lead. This system lets you talk to them naturally, and they can:
- Search the web for information
- Use an LLM to analyze and generate responses
- Ask each other for help
- Remember all past conversations

The magic? It's all built with **PocketFlow**, a minimal framework for LLM workflows that uses just 3 concepts: Nodes, Flows, and Actions.

## Architecture Overview

### The Big Picture

```
┌──────────────┐
│ User Types   │ "CTO, what database should we use?"
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ GetUserInput     │ Parses message, detects target agent
│ (AsyncNode)      │ Routes to: secretary|cto|lead_developer|qa_lead|multi_agent
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ AgentDecisionNode│ Agent thinks: "Should I search? Call LLM? Ask colleague?"
│ (AsyncNode)      │ Returns action: search|llm|broadcast|colleague|answer
└──────┬───────────┘
       │
       ├─[search]──────► SearchWebNode ──► back to agent
       ├─[llm]─────────► CallLLMNode ───► back to agent
       ├─[broadcast]───► BroadcastNode ─► back to agent
       ├─[colleague]───► RouteNode ─────► other agent
       └─[answer]──────► FinalAnswerNode ► DisplayResult ► loop back to input
```

### The Flow is a Loop

Unlike typical applications that start and stop, this system **runs forever** until you type "quit":

```
User Input → Agent Processing → Display Result → User Input → ...
```

This is achieved by wiring the display node back to the input node:
```python
display - "continue" >> get_input
```

## Core Components

### 1. The Shared Store (The Brain)

Think of this as a heap of memory shared by all nodes. It holds:

```python
shared = {
    "initial_message": "What database should we use?",
    "current_task": "What database should we use?",
    "current_agent": "cto",
    "conversation_history": [
        {"agent": "cto", "action": "search", "summary": "Searched 'best databases 2025'"},
        {"agent": "cto", "action": "llm", "summary": "Called LLM for analysis"}
    ],
    "past_conversations": [  # Loaded from log file
        # All previous interactions from conversation_log.jsonl
    ],
    "current_decision": {"action": "search", "query": "best databases 2025"},
    ...
}
```

**Key principle**: Nodes READ from shared in `prep()`, WRITE to shared in `post()`, but NEVER access shared in `exec()`.

### 2. Node Types

Every node has 3 phases (all optional):

```python
class MyNode(AsyncNode):
    async def prep_async(self, shared):
        """Phase 1: READ from shared
        - Extract what you need
        - Return it as prep_res
        """
        return shared["something"]

    async def exec_async(self, prep_res):
        """Phase 2: DO THE WORK
        - Call APIs, LLMs, search web
        - NO shared access here!
        - Can raise exceptions (retry mechanism handles it)
        """
        return await do_something(prep_res)

    async def post_async(self, shared, prep_res, exec_res):
        """Phase 3: WRITE results and decide next step
        - Update shared with results
        - Return action string for flow control
        """
        shared["result"] = exec_res
        return "success"  # This determines which node runs next
```

### 3. The Agents

Each agent is an `AgentDecisionNode` instance:

```python
cto_decide = AgentDecisionNode('cto')
dev_decide = AgentDecisionNode('lead_developer')
qa_decide = AgentDecisionNode('qa_lead')
sec_decide = AgentDecisionNode('secretary')
```

When an agent's node runs:
1. **prep**: Gathers current task + conversation history + past memory
2. **exec**: Calls LLM with agent's role config + full context, asks "What should I do?"
3. **post**: Returns action string (`"search"`, `"llm"`, `"broadcast"`, `"colleague"`, `"answer"`)

The LLM response is YAML:
```yaml
action: search
reasoning: I need current information about databases
query: best databases 2025
```

This structured output makes flow control deterministic.

### 4. Flow Wiring

PocketFlow uses a simple syntax for connecting nodes:

```python
# Default transition (when post returns "default")
node_a >> node_b

# Named transition (when post returns "search")
agent_node - "search" >> search_node

# Multiple transitions from one node
cto_decide - "search" >> search_web
cto_decide - "llm" >> call_llm_node
cto_decide - "broadcast" >> broadcast
cto_decide - "colleague" >> route
cto_decide - "answer" >> final_answer
```

This creates a **graph** where actions determine the path.

## Key Features Explained

### Feature 1: Memory System

**How it works:**

1. **Logging**: Every action writes to `conversation_log.jsonl`:
```python
log_message('decision', 'cto', 'Action: search, Reasoning: need info')
```

2. **Loading**: On first interaction, load all past logs:
```python
shared["past_conversations"] = load_conversation_history()
```

3. **Context**: Each agent decision includes past memory:
```python
prompt = f"""
{agent_config}

PAST CONVERSATIONS (Your Memory):
{format_past_logs(last_20_entries)}

CURRENT TASK:
{current_task}

What should you do?
"""
```

**Why it works**: Agents can reference "the CTO said last week..." because they literally see previous log entries.

### Feature 2: Parallel Broadcast

**The challenge**: How do you ask all agents simultaneously?

**The solution**: `AsyncParallelBatchNode`

```python
class BroadcastToAllNode(AsyncParallelBatchNode):
    async def prep_async(self, shared):
        # Return list of tasks (one per agent)
        return [
            {"agent": "cto", "message": "What's your role?"},
            {"agent": "lead_developer", "message": "What's your role?"},
            {"agent": "qa_lead", "message": "What's your role?"}
        ]

    async def exec_async(self, task):
        # Called ONCE PER TASK, ALL IN PARALLEL
        response = await call_llm(f"{task['agent_config']}\n\n{task['message']}")
        return {"agent": task["agent"], "response": response}

    async def post_async(self, shared, prep_res, exec_res_list):
        # Receives LIST of all exec results
        # Compile them into final answer
        all_responses = "\n\n".join([r["response"] for r in exec_res_list])
        shared["current_task"] = f"Responses:\n{all_responses}"
        return shared["current_agent"]  # Route back to requester
```

**Key insight**: `prep` returns a list, `exec` runs once per item (in parallel), `post` receives all results.

### Feature 3: Multi-Agent @mentions

**User types**: `@CTO @Dev evaluate this design`

**Parsing** (in GetUserInput):
```python
# Find all @mentions
at_mentions = re.findall(r'@(\w+)', message)  # ['CTO', 'Dev']

# Map to agent names
target_agents = ['cto', 'lead_developer']

# Return special routing
if len(target_agents) > 1:
    return ('multi_agent', target_agents), cleaned_message
```

**Routing**: Instead of going to a single agent decision node, go to `TargetedBroadcastNode`:
```python
get_input - "multi_agent" >> targeted_broadcast
```

**Processing**: Similar to BroadcastToAllNode, but only sends to specified agents.

### Feature 4: Dynamic Routing

**The problem**: After a search or LLM call, how do we return to the *current* agent (which might be any of the 4)?

**The solution**: Return the agent name as the action:

```python
# In SearchWebNode.post
return shared["current_agent"]  # Returns "cto" or "secretary" or ...
```

**Wiring all possible routes**:
```python
search_web - "secretary" >> sec_decide
search_web - "cto" >> cto_decide
search_web - "lead_developer" >> dev_decide
search_web - "qa_lead" >> qa_decide
```

PocketFlow follows the action string to find the next node.

## File Structure

```
exercs/09-agent/
├── main.py                    # The entire application (680 lines)
│   ├── Logging functions      (lines 31-53)
│   ├── GetUserInput node      (lines 55-158)
│   ├── AgentDecisionNode      (lines 160-226)
│   ├── Action nodes           (lines 228-520)
│   ├── Node instantiation     (lines 585-604)
│   └── Flow wiring            (lines 606-680)
│
├── config/
│   ├── cto.cf                 # CTO role definition (YAML)
│   ├── lead_developer.cf      # Dev role definition
│   ├── qa_lead.cf             # QA role definition
│   ├── secretary.cf           # Secretary role definition
│   └── guidelines.common      # Company policies
│
├── tools_llm.py               # LLM wrapper (OpenAI)
├── tools_websearch.py         # Web search (DuckDuckGo)
├── tools_debug.py             # Debug logging
│
├── conversation_log.jsonl     # Auto-generated: all interactions
│
└── [documentation files]
```

## How to Add a New Agent

Let's say you want to add a "Project Manager" agent:

**Step 1**: Create config file `config/project_manager.cf`:
```yaml
SYSTEM: |
  You are the Project Manager.

  Your role: Coordinate projects, manage timelines, track deliverables.

  CAPABILITIES:
  - You can search the web for project management tools
```

**Step 2**: Load config:
```python
AGENTS = {
    'cto': load_agent_config('cto'),
    'lead_developer': load_agent_config('lead_developer'),
    'qa_lead': load_agent_config('qa_lead'),
    'secretary': load_agent_config('secretary'),
    'project_manager': load_agent_config('project_manager'),  # Add this
}
```

**Step 3**: Create decision node:
```python
pm_decide = AgentDecisionNode('project_manager')
```

**Step 4**: Wire up all transitions:
```python
# From input
get_input - "project_manager" >> pm_decide

# From PM's decisions
pm_decide - "search" >> search_web
pm_decide - "llm" >> call_llm_node
pm_decide - "broadcast" >> broadcast
pm_decide - "colleague" >> route
pm_decide - "answer" >> final_answer

# To PM (from actions)
search_web - "project_manager" >> pm_decide
call_llm_node - "project_manager" >> pm_decide
broadcast - "project_manager" >> pm_decide
route - "project_manager" >> pm_decide
```

**Step 5**: Update parsing:
```python
agent_keywords = {
    'secretary': ['secretary', 'sec'],
    'cto': ['cto'],
    'lead_developer': ['lead developer', 'lead dev', 'developer'],
    'qa_lead': ['qa lead', 'qa'],
    'project_manager': ['project manager', 'pm'],  # Add this
}
```

Done! Now you can say: `PM, what's the status of Project X?`

## How to Add a New Action

Let's say you want agents to be able to read files:

**Step 1**: Create the action node:
```python
class ReadFileNode(AsyncNode):
    def __init__(self):
        super().__init__(max_retries=2, wait=1)

    async def prep_async(self, shared):
        filepath = shared["current_decision"]["filepath"]
        return filepath

    async def exec_async(self, filepath):
        debug(f'Reading file: {filepath}')
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, lambda: open(filepath).read())
        return content

    async def post_async(self, shared, prep_res, exec_res):
        agent = shared["current_agent"]

        # Log the action
        log_message('read_file', agent, f"File: {prep_res}")

        # Store in history
        shared["conversation_history"].append({
            'agent': agent,
            'action': 'read_file',
            'summary': f"Read file {prep_res}",
            'data': exec_res
        })

        # Add to task context
        shared["current_task"] = f"File content:\n{exec_res}\n\nOriginal task: {shared['initial_message']}"

        # Route back to agent
        return shared["current_agent"]
```

**Step 2**: Instantiate:
```python
read_file = ReadFileNode()
```

**Step 3**: Update agent decision prompt:
```python
INSTRUCTIONS:
Decide what action to take. You have 6 options:  # Changed from 5
1. search - Search the web
2. llm - Call an LLM
3. broadcast - Ask ALL team members
4. colleague - Ask ONE colleague
5. read_file - Read a file from disk  # NEW
6. answer - Provide final answer

Respond in YAML:
```yaml
action: search|llm|broadcast|colleague|read_file|answer
...
filepath: path/to/file.txt (if action=read_file)  # NEW field
...
```

**Step 4**: Wire it up:
```python
# Each agent can use it
sec_decide - "read_file" >> read_file
cto_decide - "read_file" >> read_file
dev_decide - "read_file" >> read_file
qa_decide - "read_file" >> read_file

# Route back to each agent
read_file - "secretary" >> sec_decide
read_file - "cto" >> cto_decide
read_file - "lead_developer" >> dev_decide
read_file - "qa_lead" >> qa_decide
```

Done! Agents can now say: `action: read_file, filepath: config/database.yaml`

## Common Patterns

### Pattern 1: Retry on Failure

```python
class UnreliableAPINode(AsyncNode):
    def __init__(self):
        super().__init__(max_retries=3, wait=5)  # Retry 3 times, wait 5s

    async def exec_async(self, data):
        # May raise exception
        return await flaky_api_call(data)

    async def exec_fallback_async(self, data, error):
        # Called after all retries fail
        return f"API failed after 3 attempts: {error}"
```

No try/except needed! The framework handles retries automatically.

### Pattern 2: Conditional Routing

```python
class ValidateNode(AsyncNode):
    async def exec_async(self, data):
        score = validate(data)
        return score

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res > 0.9:
            return "excellent"
        elif exec_res > 0.7:
            return "good"
        else:
            return "needs_work"

# Wire different paths
validate - "excellent" >> celebrate_node
validate - "good" >> accept_node
validate - "needs_work" >> improve_node
```

### Pattern 3: Batch Processing

```python
class ProcessFilesNode(BatchNode):
    def prep(self, shared):
        # Return a LIST
        return shared["file_list"]

    def exec(self, single_file):
        # Called ONCE per file (sequentially)
        return process(single_file)

    def post(self, shared, prep_res, exec_res_list):
        # Receives LIST of all results
        shared["results"] = exec_res_list
```

For parallel: use `AsyncParallelBatchNode` instead.

## Debugging Tips

### 1. Use Debug Logging

```python
from tools_debug import debug

debug(f'Current agent: {agent_name}')
debug(f'Decision: {decision}')
```

Outputs to stderr with file/line info:
```
>>> [/path/main.py] post_async(): [156] Routing message to: CTO
```

### 2. Inspect the Log File

```bash
# Pretty-print all logs
cat conversation_log.jsonl | jq

# Find when CTO made decisions
cat conversation_log.jsonl | jq 'select(.agent == "cto" and .type == "decision")'

# See conversation flow
cat conversation_log.jsonl | jq -r '"\(.timestamp) [\(.agent)] \(.type): \(.content)"'
```

### 3. Add Temporary Print Statements

In any node's post method:
```python
async def post_async(self, shared, prep_res, exec_res):
    print(f"DEBUG: shared keys = {list(shared.keys())}")
    print(f"DEBUG: exec_res = {exec_res}")
    ...
```

### 4. Test Nodes in Isolation

```python
# Test a single node without the full flow
node = SearchWebNode()
shared = {"current_decision": {"query": "test"}}

prep_res = await node.prep_async(shared)
exec_res = await node.exec_async(prep_res)
action = await node.post_async(shared, prep_res, exec_res)

print(f"Action returned: {action}")
print(f"Shared updated: {shared}")
```

## Performance Considerations

### Async vs Sync

The system uses `AsyncFlow` and `AsyncNode` because:
1. Web searches take 1-3 seconds
2. LLM calls take 2-5 seconds
3. Parallel broadcasts save time (3 agents in parallel = 5s vs sequential = 15s)

If you add sync operations, wrap them:
```python
async def exec_async(self, data):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: sync_function(data))
    return result
```

### Rate Limiting

OpenAI has rate limits. If agents make many LLM calls:

```python
import asyncio

class RateLimitedLLMNode(AsyncNode):
    last_call = 0
    min_interval = 1.0  # 1 second between calls

    async def exec_async(self, prompt):
        # Wait if needed
        elapsed = time.time() - RateLimitedLLMNode.last_call
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)

        result = call_llm(prompt)
        RateLimitedLLMNode.last_call = time.time()
        return result
```

### Memory Growth

`past_conversations` loads ALL logs. If this grows large:

```python
def load_conversation_history(limit=100):
    """Load only recent entries"""
    if not LOG_FILE.exists():
        return []

    history = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            if line.strip():
                history.append(json.loads(line))

    return history[-limit:]  # Only last 100 entries
```

## Testing Strategies

### Unit Test a Node

```python
import pytest
from main import SearchWebNode

@pytest.mark.asyncio
async def test_search_node():
    node = SearchWebNode()
    shared = {
        "current_agent": "cto",
        "current_decision": {"query": "python testing"},
        "conversation_history": [],
        "initial_message": "test"
    }

    prep_res = await node.prep_async(shared)
    assert prep_res == "python testing"

    exec_res = await node.exec_async(prep_res)
    assert isinstance(exec_res, list)
    assert len(exec_res) > 0

    action = await node.post_async(shared, prep_res, exec_res)
    assert action == "cto"
    assert len(shared["conversation_history"]) == 1
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_full_interaction():
    from main import get_input, sec_decide, final_answer, display

    shared = {}

    # Simulate user input
    # (Would need to mock input() function)

    # Run flow manually
    await get_input.run_async(shared)
    assert shared["current_agent"] == "secretary"

    # ... continue through flow
```

### Mock External Services

```python
from unittest.mock import patch

@patch('main.call_llm')
@pytest.mark.asyncio
async def test_agent_decision(mock_llm):
    mock_llm.return_value = """```yaml
action: answer
reasoning: test
answer: Hello!
```"""

    node = AgentDecisionNode('cto')
    shared = {"current_task": "say hello", "conversation_history": [], "past_conversations": []}

    prep_res = await node.prep_async(shared)
    exec_res = await node.exec_async(prep_res)

    assert exec_res["action"] == "answer"
    assert "Hello" in exec_res["answer"]
```

## Best Practices

### 1. Keep Nodes Focused

❌ **Don't**:
```python
class GodNode(Node):
    def exec(self, data):
        search_results = search_web(data)
        llm_response = call_llm(search_results)
        validated = validate(llm_response)
        return validated
```

✅ **Do**:
```python
search_node >> llm_node >> validate_node
```

### 2. Use Descriptive Action Names

❌ **Don't**: `return "ok"`
✅ **Do**: `return "validation_passed"`

### 3. Log Important Events

```python
log_message('decision', agent, f"Chose to search for: {query}")
```

Helps debugging and provides audit trail.

### 4. Structure Shared Store

❌ **Don't**:
```python
shared = {
    "data1": ...,
    "data2": ...,
    "temp": ...,
    "x": ...,
}
```

✅ **Do**:
```python
shared = {
    "user": {
        "input": "...",
        "preferences": {}
    },
    "agents": {
        "current": "cto",
        "history": []
    },
    "state": {
        "hop_count": 0,
        "max_hops": 15
    }
}
```

### 5. Handle Edge Cases

```python
async def post_async(self, shared, prep_res, exec_res):
    # Check for empty results
    if not exec_res or len(exec_res) == 0:
        shared["current_task"] = "No results found, please provide answer directly"
        return shared["current_agent"]

    # Normal processing
    ...
```

## Conclusion

This system demonstrates how PocketFlow's simple primitives (Nodes, Actions, Flows) can build complex agentic systems. The key insights:

1. **Separation of Concerns**: prep/exec/post makes code clean and testable
2. **Action-Based Routing**: Post methods return strings that control flow
3. **Async for Performance**: Parallel operations when possible
4. **Memory Through Logs**: Simple file-based persistence
5. **LLM for Decisions**: Structured YAML output for deterministic routing

To extend it, follow the patterns:
- New agent? Add config + node + wiring
- New action? Add node + update prompts + wire to all agents
- New feature? Think: "Which node? Which phase?"

Happy coding! 🚀
