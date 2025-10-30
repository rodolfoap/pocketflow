# Technical Specifications: Multi-Agent System

> Complete technical specifications for rebuilding this system from scratch following PocketFlow best practices

## System Overview

**Name**: Multi-Agent Team Communication System
**Framework**: PocketFlow (Async)
**Language**: Python 3.8+
**Architecture**: Event-driven flow control with persistent memory
**Pattern**: Agent-based decision-making with dynamic routing

### High-Level Description

A persistent, memory-enabled multi-agent system where a user (Leader) can communicate with 4 specialized AI agents (Secretary, CTO, Lead Developer, QA Lead). Agents can search the web, call LLMs, broadcast to all team members, delegate to specific colleagues, and provide answers. All interactions are logged to disk and loaded as memory for future sessions.

## Core Requirements

### FR-1: Multi-Agent Communication
- System must support 4 distinct agents, each with specific roles
- User must be able to address any single agent directly
- User must be able to address multiple agents simultaneously (@mentions)
- Default routing to Secretary if no agent specified

### FR-2: Agent Capabilities
Each agent must support 5 actions:
1. **search** - Search the web for information
2. **llm** - Call an LLM with custom prompts
3. **broadcast** - Ask ALL team members for input (parallel)
4. **colleague** - Delegate to ONE specific colleague
5. **answer** - Provide final answer to user

### FR-3: Memory System
- All interactions must be logged to `conversation_log.jsonl` (JSON Lines format)
- On startup, load all past conversations from log file
- Each agent must have access to past conversation history
- Memory must persist across application restarts
- Format: conversation-style (natural language) not raw logs

### FR-4: Interactive Loop
- System runs continuously until user types quit/exit/q
- Flow: `Input → Processing → Display → Input` (loop)
- Each iteration maintains shared state but resets per-interaction state

### FR-5: Async Processing
- Use AsyncFlow and AsyncNode for all operations
- Parallel processing for broadcasts (AsyncParallelBatchNode)
- Wrap sync functions (LLM, web search) with asyncio.run_in_executor

## Architecture Specifications

### PocketFlow Best Practices Applied

#### 1. Node Structure (3-Phase Pattern)
```python
class ExampleNode(AsyncNode):
    async def prep_async(self, shared):
        """Phase 1: READ from shared store
        - Extract needed data
        - No side effects
        - Return prep_res
        """
        return shared["something"]

    async def exec_async(self, prep_res):
        """Phase 2: EXECUTE computation
        - NO shared access here
        - Can raise exceptions (retry handles it)
        - Pure computation or I/O
        """
        return await do_work(prep_res)

    async def post_async(self, shared, prep_res, exec_res):
        """Phase 3: WRITE and decide next step
        - Update shared store
        - Log results
        - Return action string for routing
        """
        shared["result"] = exec_res
        return "success"  # Determines next node
```

#### 2. Separation of Concerns
- **prep**: READ only
- **exec**: COMPUTE only (no shared access)
- **post**: WRITE and ROUTE

#### 3. No Try/Except in exec
Let PocketFlow's retry mechanism handle exceptions:
```python
async def exec_async(self, data):
    # Don't catch exceptions - let retry mechanism work
    return await flaky_api_call(data)

async def exec_fallback_async(self, data, error):
    # Called after all retries fail
    return f"Fallback result: {error}"
```

#### 4. Action-Based Routing
Use returned strings to control flow:
```python
node_a - "success" >> node_b
node_a - "failure" >> node_c
```

#### 5. Shared Store Schema
Well-structured dictionary, not flat:
```python
shared = {
    "user": {
        "initial_message": str,
        "current_task": str
    },
    "state": {
        "current_agent": str,
        "current_hop": int,
        "max_hops": int
    },
    "memory": {
        "conversation_history": list,  # Current interaction
        "past_conversations": list     # All history
    },
    "decisions": {
        "current_decision": dict
    }
}
```

## Component Specifications

### 1. Agents

#### Agent Roles
Each agent has:
- **Config file** (YAML): `config/{agent_name}.cf`
- **Role description**: What they do
- **Capabilities**: What tools they can use
- **Guidelines**: Company-wide policies

**Required Agents:**
| Name | ID | Role |
|------|-----|------|
| Secretary | `secretary` | Admin, coordination, research |
| CTO | `cto` | Technical strategy, architecture |
| Lead Developer | `lead_developer` | Implementation, coding |
| QA Lead | `qa_lead` | Testing, quality assurance |

#### Config File Format (YAML)
```yaml
SYSTEM: |
  You are the <Role Name>.

  Your role: <Brief description>

  IMPORTANT:
  - Only work on tasks assigned to you
  - Answer only what is asked
  - Be brief and focused

  CAPABILITIES:
  - You can search the web using web_search tool

  You follow the Company Guidelines.
```

#### Agent Keywords for Routing
```python
AGENT_KEYWORDS = {
    'secretary': ['secretary', 'sec'],
    'cto': ['cto', 'chief technology officer'],
    'lead_developer': ['lead developer', 'lead dev', 'developer'],
    'qa_lead': ['qa lead', 'qa', 'quality assurance']
}

AT_MENTION_MAP = {
    'secretary': 'secretary', 'sec': 'secretary',
    'cto': 'cto',
    'dev': 'lead_developer', 'developer': 'lead_developer',
    'lead_dev': 'lead_developer', 'lead_developer': 'lead_developer',
    'qa': 'qa_lead', 'qa_lead': 'qa_lead'
}
```

### 2. Node Specifications

#### GetUserInput (AsyncNode)
**Purpose**: Get user input and route to appropriate agent(s)

**Input**: None (reads from stdin)

**Output Actions**:
- `secretary` | `cto` | `lead_developer` | `qa_lead` - Route to single agent
- `multi_agent` - Route to targeted broadcast
- `quit` - Exit application

**Logic**:
1. Read input from stdin
2. Check for quit commands
3. Parse @mentions or direct agent names
4. Clean message (remove agent names)
5. Load past conversations (first time only)
6. Reset per-interaction state
7. Log user input
8. Return routing action

**Shared Store Updates**:
```python
shared["initial_message"] = cleaned_message
shared["current_task"] = cleaned_message
shared["current_agent"] = target_agent
shared["conversation_history"] = []
shared["past_conversations"] = load_conversation_history()  # First time
shared["target_agents"] = [...]  # For multi-agent
```

#### AgentDecisionNode (AsyncNode)
**Purpose**: Agent decides what action to take

**Constructor**: `__init__(self, agent_name: str)`
- `agent_name`: One of ['secretary', 'cto', 'lead_developer', 'qa_lead']
- `max_retries`: 2
- `wait`: 3 seconds

**Input** (from prep):
```python
{
    'task': str,                    # Current task
    'history': list,                # Current interaction history
    'past_conversations': list,     # All past conversations
    'agent_config': str            # Agent's role config
}
```

**Processing** (in exec):
1. Format past conversations into natural language
2. Build LLM prompt with:
   - Agent config
   - Past conversations (memory)
   - Current interaction history
   - Current task
   - Action options (5 choices)
3. Call LLM
4. Parse YAML response

**LLM Prompt Structure**:
```
{agent_config}

PAST CONVERSATIONS (Your Memory):
{formatted_past_logs}

CURRENT INTERACTION HISTORY:
{current_history}

CURRENT TASK ASSIGNED TO YOU:
{task}

INSTRUCTIONS:
Decide what action to take. You have 5 options:
1. search - Search the web for information
2. llm - Write a prompt and query an LLM for analysis/generation
3. broadcast - Ask ALL team members (in parallel) for their input/roles/status
4. colleague - Ask ONE specific colleague (cto, lead_developer, qa_lead, secretary) for help
5. answer - Provide the final answer to complete the task

Respond ONLY with valid YAML in this exact format:
```yaml
action: search|llm|broadcast|colleague|answer
reasoning: brief explanation of your decision
query: the search query (if action=search)
prompt: the LLM prompt (if action=llm)
broadcast_message: what you're asking all team members (if action=broadcast)
colleague: cto|lead_developer|qa_lead|secretary (if action=colleague)
delegation_message: what you're asking the colleague (if action=colleague)
answer: your final response (if action=answer)
```
```

**Output Actions**: `search` | `llm` | `broadcast` | `colleague` | `answer`

**Shared Store Updates**:
```python
shared["current_decision"] = exec_res  # Parsed YAML
shared["current_hop"] += 1
```

**Hop Limit**: If `current_hop >= max_hops`, force action to "answer"

#### SearchWebNode (AsyncNode)
**Purpose**: Perform web search

**Constructor**:
- `max_retries`: 2
- `wait`: 2 seconds

**Input** (from prep): `query: str`

**Processing**:
```python
results = websearch(query, max_results=3, crawl=False)
# Returns list of {"title", "href", "body"}
```

**Output Action**: Returns `shared["current_agent"]` (dynamic routing back)

**Shared Store Updates**:
```python
shared["conversation_history"].append({
    'agent': agent,
    'action': 'search',
    'summary': f"Searched '{query}', found {len(results)} results",
    'data': results
})

shared["current_task"] = f"Web search results:\n{formatted_results}\n\nOriginal task: {initial_message}"
```

**Logging**: `log_message('search', agent, f"Query: {query}", {'results_count': len(results)})`

#### CallLLMNode (AsyncNode)
**Purpose**: Call LLM with custom prompt

**Constructor**:
- `max_retries`: 2
- `wait`: 3 seconds

**Input** (from prep): `prompt: str`

**Processing**:
```python
response = call_llm(prompt)
```

**Output Action**: Returns `shared["current_agent"]` (dynamic routing back)

**Shared Store Updates**:
```python
shared["conversation_history"].append({
    'agent': agent,
    'action': 'llm',
    'summary': f"Called LLM, got response ({len(response)} chars)",
    'data': response
})

shared["current_task"] = f"LLM response:\n{response}\n\nOriginal task: {initial_message}"
```

**Logging**: `log_message('llm_call', agent, f"Prompt length: {len(prompt)} chars, Response length: {len(response)} chars")`

#### BroadcastToAllNode (AsyncParallelBatchNode)
**Purpose**: Send message to ALL other team members in parallel

**Input** (from prep): List of tasks
```python
[
    {'agent': 'cto', 'message': str, 'agent_config': str},
    {'agent': 'lead_developer', 'message': str, 'agent_config': str},
    {'agent': 'qa_lead', 'message': str, 'agent_config': str}
]
# Excludes the requesting agent
```

**Processing** (per item, in parallel):
```python
prompt = f"""{agent_config}

You have received a request from a colleague:
{message}

Respond briefly and directly to this request. Be concise.
"""
response = call_llm(prompt)
return {'agent': agent_name, 'response': response}
```

**Output Action**: Returns `requester_agent` (route back to requester)

**Shared Store Updates**:
```python
shared["conversation_history"].append({
    'agent': requester,
    'action': 'broadcast',
    'summary': f"Broadcast to {len(responses)} team members",
    'data': responses
})

shared["current_task"] = f"Broadcast responses received:\n\n{compiled_responses}\n\nOriginal request: {initial_message}"
shared["current_agent"] = requester
```

**Logging**:
```python
log_message('broadcast', requester, f"Broadcast to {len(responses)} agents")
for response in responses:
    log_message('broadcast_response', response['agent'], response['response'][:200])
```

#### TargetedBroadcastNode (AsyncParallelBatchNode)
**Purpose**: Send message to SELECTED team members in parallel

**Input** (from prep): List of tasks for specified agents only
```python
[
    {'agent': 'cto', 'message': str, 'agent_config': str},
    {'agent': 'lead_developer', 'message': str, 'agent_config': str}
]
# Only agents mentioned with @
```

**Processing**: Same as BroadcastToAllNode

**Output Action**: `"done"` (goes directly to display)

**Special**: Sets `shared["final_answer"]` directly with compiled responses

**Logging**:
```python
log_message('targeted_broadcast', 'user', f"To {len(responses)} agents")
for response in responses:
    log_message('targeted_broadcast_response', response['agent'], response['response'][:200])
```

#### RouteToColleagueNode (AsyncNode)
**Purpose**: Delegate task to one specific colleague

**Input** (from prep): None

**Processing**: None (just routing)

**Output Action**: Returns `colleague_name` (e.g., "cto", "lead_developer")

**Shared Store Updates**:
```python
shared["conversation_history"].append({
    'agent': current_agent,
    'action': f'delegate_to_{colleague}',
    'summary': delegation_message,
    'data': None
})

shared["current_agent"] = colleague
shared["current_task"] = delegation_message
```

**Logging**: `log_message('delegation', agent, f"To {colleague}: {message}")`

#### FinalAnswerNode (AsyncNode)
**Purpose**: Extract and finalize answer

**Input** (from prep): `answer: str` (from decision)

**Processing**: None (passthrough)

**Output Action**: `"done"`

**Shared Store Updates**:
```python
shared["final_answer"] = answer

shared["conversation_history"].append({
    'agent': agent,
    'action': 'answer',
    'summary': "Provided final answer",
    'data': answer
})
```

**Logging**: `log_message('final_answer', agent, answer)`

#### DisplayResult (AsyncNode)
**Purpose**: Display final result and loop back

**Input**: None

**Processing**: Print formatted result to stdout
```
============================================================
FINAL ANSWER:
============================================================
{final_answer}

============================================================
CONVERSATION SUMMARY ({N} steps):
============================================================
1. [AGENT] action: summary
2. [AGENT] action: summary
...
============================================================
```

**Output Action**: `"continue"` (loop back to input)

**Logging**: `log_message('interaction_complete', 'system', f"Completed in {N} steps")`

#### QuitNode (AsyncNode)
**Purpose**: Handle graceful exit

**Processing**: Print exit message

**Output Action**: `"default"` (ends flow)

### 3. Flow Wiring Specification

```python
# User input routing
get_input - "secretary" >> sec_decide
get_input - "cto" >> cto_decide
get_input - "lead_developer" >> dev_decide
get_input - "qa_lead" >> qa_decide
get_input - "multi_agent" >> targeted_broadcast
get_input - "quit" >> quit_node

# Each agent's decision routing
for agent_decide in [sec_decide, cto_decide, dev_decide, qa_decide]:
    agent_decide - "search" >> search_web
    agent_decide - "llm" >> call_llm_node
    agent_decide - "broadcast" >> broadcast
    agent_decide - "colleague" >> route
    agent_decide - "answer" >> final_answer

# Search/LLM back to agents (dynamic routing)
for agent_name in ["secretary", "cto", "lead_developer", "qa_lead"]:
    search_web - agent_name >> get_decide_node(agent_name)
    call_llm_node - agent_name >> get_decide_node(agent_name)
    broadcast - agent_name >> get_decide_node(agent_name)

# Colleague routing
route - "cto" >> cto_decide
route - "lead_developer" >> dev_decide
route - "qa_lead" >> qa_decide
route - "secretary" >> sec_decide

# Answer and display
final_answer - "done" >> display
targeted_broadcast - "done" >> display

# Loop back
display - "continue" >> get_input
```

### 4. Logging System

#### Log File Format
- **Filename**: `conversation_log.jsonl`
- **Format**: JSON Lines (one JSON object per line)

#### Log Entry Schema
```json
{
    "timestamp": "2025-10-30T12:34:56.789012",
    "type": "user_input|decision|search|llm_call|broadcast|broadcast_response|targeted_broadcast|targeted_broadcast_response|delegation|final_answer|interaction_complete",
    "agent": "user|secretary|cto|lead_developer|qa_lead|system",
    "content": "Human-readable summary string",
    "data": {}  // Optional: structured data
}
```

#### Log Types
| Type | Agent | Content | Data |
|------|-------|---------|------|
| `user_input` | user | "To {agent}: {message}" | null |
| `decision` | agent | "Action: {action}, Reasoning: {reasoning}" | Full YAML |
| `search` | agent | "Query: {query}" | {'results_count': N} |
| `llm_call` | agent | "Prompt length: X, Response length: Y" | null |
| `broadcast` | agent | "Broadcast to N agents" | null |
| `broadcast_response` | agent | Response text (truncated) | null |
| `targeted_broadcast` | user | "To N agents" | null |
| `targeted_broadcast_response` | agent | Response text (truncated) | null |
| `delegation` | agent | "To {colleague}: {message}" | null |
| `final_answer` | agent | Full answer text | null |
| `interaction_complete` | system | "Completed in N steps" | null |

#### Logging Functions
```python
def log_message(message_type: str, agent: str, content: str, data: dict = None):
    """Write log entry to conversation_log.jsonl"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': message_type,
        'agent': agent,
        'content': content,
        'data': data
    }
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def load_conversation_history() -> list:
    """Load all past logs from conversation_log.jsonl"""
    if not LOG_FILE.exists():
        return []

    history = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            if line.strip():
                history.append(json.loads(line))
    return history
```

### 5. Memory System

#### Memory Loading
- On first interaction, call `load_conversation_history()`
- Store in `shared["past_conversations"]`
- Keep for entire session
- Reload on application restart

#### Memory Formatting
Convert logs to natural conversation format:

**Input** (raw log):
```json
{"type": "user_input", "agent": "user", "content": "To cto: CTO, My name is James."}
{"type": "final_answer", "agent": "cto", "content": "Nice to meet you, James!"}
```

**Output** (formatted for LLM):
```
[2025-10-30 12:34:56] Leader said: My name is James.
[2025-10-30 12:35:01] CTO responded: Nice to meet you, James!
```

#### Formatting Algorithm
```python
def format_past_conversations(logs):
    formatted = []

    for log in logs[-30:]:  # Last 30 entries
        if log['type'] == 'user_input':
            # Parse "To agent: Agent_Name, actual message"
            message = extract_clean_message(log['content'])
            formatted.append(f"\n[{timestamp}] Leader said: {message}")

        elif log['type'] == 'final_answer':
            formatted.append(f"[{timestamp}] {agent.upper()} responded: {content[:300]}")

        elif log['type'] == 'broadcast_response':
            formatted.append(f"[{timestamp}] {agent.upper()} said: {content[:200]}")

        elif log['type'] == 'search':
            formatted.append(f"[{timestamp}] {agent.upper()} searched: {content}")

        elif log['type'] == 'delegation':
            formatted.append(f"[{timestamp}] {agent.upper()} delegated: {content}")

    return "\n".join(formatted)
```

## External Dependencies

### Required Python Packages
```
pocketflow>=1.0.0
openai>=1.0.0
ddgs  # DuckDuckGo Search
beautifulsoup4
pyyaml
```

### External APIs
1. **OpenAI API**
   - Used for LLM calls
   - Model: `gpt-4o` (configurable)
   - Requires API key in environment: `OPENAI_API_KEY`

2. **DuckDuckGo Search**
   - Web search functionality
   - No API key required
   - May rate limit on excessive use

### Utility Modules

#### tools_llm.py
```python
from openai import OpenAI
import os

def call_llm(prompt: str, model: str = "gpt-4o") -> str:
    """Call OpenAI LLM with prompt"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

#### tools_websearch.py
```python
from ddgs import DDGS
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re

def websearch(query: str, max_results: int = 3, crawl: bool = False) -> list:
    """Search web and optionally crawl pages"""
    answers = DDGS(timeout=3).text(query, max_results=max_results)

    if not crawl:
        return answers

    # Crawl pages and add 'text' field
    results = []
    for result in answers:
        result['text'] = getpage(result['href'])
        results.append(result)
    return results

def getpage(url: str) -> str:
    """Fetch and clean webpage content"""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urlopen(req)
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup(["script", "style"]):
        script.extract()
    return cleanup(soup.get_text())

def cleanup(text: str) -> str:
    """Clean text: remove special chars, normalize whitespace"""
    text = re.sub('[^a-zA-Z0-9@_,.$£+]', ' ', text).strip()
    text = re.sub("\\n"," ",text)
    text = re.sub("\\t"," ",text)
    text = re.sub("\\s+"," ",text)
    return text
```

#### tools_debug.py
```python
import inspect, sys

def debug(message: str = ""):
    """Print debug message with file/line info to stderr"""
    fi = inspect.getframeinfo((inspect.stack()[1])[0])
    print(f">>> [{fi.filename}] {fi.function}(): [{fi.lineno}] {message}",
          file=sys.stderr)
```

## Configuration Files

### Directory Structure
```
config/
├── cto.cf                    # CTO role config
├── lead_developer.cf         # Developer role config
├── qa_lead.cf               # QA role config
├── secretary.cf             # Secretary role config
└── guidelines.common        # Company-wide guidelines (plain text)
```

### Config Loading
```python
def load_agent_config(agent_name: str) -> str:
    """Load agent config + common guidelines"""
    with open(f'config/{agent_name}.cf', 'r') as f:
        config = yaml.safe_load(f)
    with open('config/guidelines.common', 'r') as f:
        guidelines = f.read()
    return config['SYSTEM'] + "\n\n" + guidelines

AGENTS = {
    'cto': load_agent_config('cto'),
    'lead_developer': load_agent_config('lead_developer'),
    'qa_lead': load_agent_config('qa_lead'),
    'secretary': load_agent_config('secretary')
}
```

## Entry Point

```python
async def main():
    flow = AsyncFlow(start=get_input)
    shared = {}
    await flow.run_async(shared)

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Characteristics

### Time Complexity
- **Single agent query**: 2-5 seconds (LLM decision + action)
- **Web search**: +1-3 seconds
- **Broadcast (4 agents)**: ~5 seconds (parallel, limited by slowest agent)
- **Targeted broadcast (2-3 agents)**: ~3-5 seconds (parallel)

### Space Complexity
- **Log file growth**: ~200 bytes per log entry
- **Memory per interaction**: ~50-100 log entries loaded (last 30 shown to agents)
- **Total memory**: O(N) where N = number of interactions

### Scalability Considerations
- Log file will grow indefinitely (consider rotation after X entries)
- Memory window (30 entries) prevents context overflow
- Parallel broadcasts scale to O(1) time complexity (vs O(N) sequential)

## Testing Requirements

### Unit Tests Required
1. Message parsing (@mentions, direct address)
2. Memory formatting (log → conversation format)
3. Each node's prep/exec/post in isolation
4. YAML parsing from LLM responses

### Integration Tests Required
1. Full single-agent interaction
2. Multi-agent broadcast
3. Memory persistence across restart
4. Loop behavior (multiple interactions)

### Mock Requirements
- Mock `call_llm()` to return predictable YAML
- Mock `websearch()` to return test results
- Mock `input()` for automated testing

## Error Handling

### Retry Strategy
- **LLM calls**: 2 retries, 3 second wait
- **Web searches**: 2 retries, 2 second wait
- **Fallback**: Use `exec_fallback_async()` for graceful degradation

### Error Scenarios
1. **LLM returns invalid YAML**: Retry, fallback to simple answer
2. **Web search timeout**: Return empty results, agent can decide to answer anyway
3. **Rate limiting**: Wait periods handled by retry mechanism
4. **Invalid agent name**: Default to secretary
5. **Hop limit exceeded**: Force answer action

## Security Considerations

1. **API Keys**: Never log or expose OpenAI API key
2. **Input Validation**: Sanitize user input before logging
3. **URL Fetching**: Only fetch from search results, timeout on slow pages
4. **Log File**: Ensure proper permissions (readable only by application)

## Deployment Requirements

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."
```

### File System
- Write permissions for current directory (log file)
- Read permissions for `config/` directory

### Dependencies Installation
```bash
pip install pocketflow openai ddgs beautifulsoup4 pyyaml
```

## Extension Points

### Adding New Agent
1. Create `config/new_agent.cf`
2. Add to `AGENTS` dict
3. Create `AgentDecisionNode('new_agent')`
4. Wire all 5 actions to/from new agent
5. Add keywords to parsing logic

### Adding New Action
1. Create new AsyncNode subclass
2. Update agent decision prompt (add 6th option)
3. Update YAML schema
4. Wire action to all agents
5. Wire all agents back to action node
6. Add logging

### Adding New Capability
- Extend node's `exec_async()` with new tool/API
- Update agent configs to mention new capability
- Log new action type

## Version Requirements

- **Python**: 3.8+
- **PocketFlow**: 1.0.0+
- **OpenAI**: 1.0.0+

## Success Criteria

✅ User can address any agent directly
✅ User can address multiple agents with @mentions
✅ Agents remember past conversations
✅ Memory persists across restarts
✅ Agents can search, use LLM, broadcast, delegate, answer
✅ Parallel broadcasts complete in O(1) time
✅ System runs in continuous loop
✅ All interactions logged to disk
✅ Follows PocketFlow best practices
✅ No try/except in exec methods
✅ Clean separation: prep/exec/post
✅ Action-based routing

---

**Document Version**: 1.0
**Last Updated**: 2025-10-30
**Specification Status**: Complete - Ready for Implementation
