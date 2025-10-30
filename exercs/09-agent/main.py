from pocketflow import AsyncFlow, AsyncNode, AsyncParallelBatchNode
from tools_llm import call_llm
from tools_websearch import websearch
from tools_debug import debug
import yaml
import asyncio

# Load agent configurations
def load_agent_config(agent_name):
	"""Load agent config from config directory"""
	with open(f'config/{agent_name}.cf', 'r') as f:
		config = yaml.safe_load(f)
	with open('config/guidelines.common', 'r') as f:
		guidelines = f.read()
	return config['SYSTEM'] + "\n\n" + guidelines

# Initialize agent configs
AGENTS = {
	'cto': load_agent_config('cto'),
	'lead_developer': load_agent_config('lead_developer'),
	'qa_lead': load_agent_config('qa_lead'),
	'secretary': load_agent_config('secretary')
}

class GetUserInput(AsyncNode):
	"""Get initial user message and assign to first agent"""
	async def exec_async(self, prep_res):
		return input("\n[User] Message: ")

	async def post_async(self, shared, prep_res, exec_res):
		shared["initial_message"] = exec_res
		shared["current_task"] = exec_res
		shared["current_agent"] = "secretary"  # Start with secretary
		shared["conversation_history"] = []
		shared["final_answer"] = None
		shared["max_hops"] = 15
		shared["current_hop"] = 0
		shared["requester_agent"] = None  # Track who requested broadcast
		return "default"

class AgentDecisionNode(AsyncNode):
	"""Agent decides: search web, call LLM, broadcast to all, ask one colleague, or answer"""
	def __init__(self, agent_name):
		super().__init__(max_retries=2, wait=3)
		self.agent_name = agent_name

	async def prep_async(self, shared):
		return {
			'task': shared["current_task"],
			'history': shared["conversation_history"],
			'agent_config': AGENTS[self.agent_name]
		}

	async def exec_async(self, prep_res):
		debug(f'[{self.agent_name.upper()}] Thinking...')

		prompt = f"""{prep_res['agent_config']}

CONVERSATION HISTORY:
{self._format_history(prep_res['history'])}

CURRENT TASK ASSIGNED TO YOU:
{prep_res['task']}

INSTRUCTIONS:
Decide what action to take. You have 5 options:
1. search - Search the web for information
2. llm - Write a prompt and query an LLM for analysis/generation
3. broadcast - Ask ALL team members (in parallel) for their input/roles/status
4. colleague - Ask ONE specific colleague (cto, lead_developer, qa_lead, secretary) for help
5. answer - Provide the final answer to complete the task

IMPORTANT:
- Use 'broadcast' when you need information from ALL team members (e.g., "ask everyone for their roles")
- Use 'colleague' when you need help from ONE specific person

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
```"""

		response = call_llm(prompt)
		yaml_str = response.split("```yaml")[1].split("```")[0].strip()
		return yaml.safe_load(yaml_str)

	def _format_history(self, history):
		if not history:
			return "No previous actions"
		return "\n".join([f"- [{h['agent']}] {h['action']}: {h['summary']}" for h in history])

	async def post_async(self, shared, prep_res, exec_res):
		action = exec_res['action']
		shared["current_decision"] = exec_res

		# Check hop limit
		shared["current_hop"] += 1
		if shared["current_hop"] >= shared["max_hops"]:
			debug(f"Max hops reached, forcing answer")
			return "answer"

		debug(f'[{self.agent_name.upper()}] Decision: {action} - {exec_res.get("reasoning", "")}')
		return action

class SearchWebNode(AsyncNode):
	"""Perform web search"""
	def __init__(self):
		super().__init__(max_retries=2, wait=2)

	async def prep_async(self, shared):
		query = shared["current_decision"]["query"]
		return query

	async def exec_async(self, query):
		debug(f'Searching web for: {query}')
		# Run sync function in executor
		loop = asyncio.get_event_loop()
		results = await loop.run_in_executor(None, lambda: websearch(query, max_results=3, crawl=False))
		return results

	async def exec_fallback_async(self, query, error):
		debug(f'Web search failed: {error}')
		return []

	async def post_async(self, shared, prep_res, exec_res):
		agent = shared["current_agent"]
		summary = f"Searched '{prep_res}', found {len(exec_res)} results"

		shared["conversation_history"].append({
			'agent': agent,
			'action': 'search',
			'summary': summary,
			'data': exec_res
		})

		# Prepare results for next decision
		results_text = "\n\n".join([f"Title: {r['title']}\nURL: {r['href']}\nSummary: {r['body']}"
		                            for r in exec_res])
		shared["current_task"] = f"Web search results:\n{results_text}\n\nOriginal task: {shared['initial_message']}"

		# Route back to current agent
		return shared["current_agent"]

class CallLLMNode(AsyncNode):
	"""Call LLM with custom prompt"""
	def __init__(self):
		super().__init__(max_retries=2, wait=3)

	async def prep_async(self, shared):
		prompt = shared["current_decision"]["prompt"]
		return prompt

	async def exec_async(self, prompt):
		debug(f'Calling LLM...')
		# Run sync function in executor
		loop = asyncio.get_event_loop()
		result = await loop.run_in_executor(None, lambda: call_llm(prompt))
		return result

	async def post_async(self, shared, prep_res, exec_res):
		agent = shared["current_agent"]
		summary = f"Called LLM, got response ({len(exec_res)} chars)"

		shared["conversation_history"].append({
			'agent': agent,
			'action': 'llm',
			'summary': summary,
			'data': exec_res
		})

		# Add LLM response to task context
		shared["current_task"] = f"LLM response:\n{exec_res}\n\nOriginal task: {shared['initial_message']}"

		# Route back to current agent
		return shared["current_agent"]

class BroadcastToAllNode(AsyncParallelBatchNode):
	"""Broadcast message to all team members in parallel"""
	async def prep_async(self, shared):
		broadcast_message = shared["current_decision"]["broadcast_message"]
		requester = shared["current_agent"]

		# Store who requested the broadcast
		shared["requester_agent"] = requester

		# Create tasks for all OTHER agents (not the requester)
		agents = ['cto', 'lead_developer', 'qa_lead', 'secretary']
		tasks = []
		for agent in agents:
			if agent != requester:  # Don't ask yourself
				tasks.append({
					'agent': agent,
					'message': broadcast_message,
					'agent_config': AGENTS[agent]
				})

		debug(f'[{requester.upper()}] Broadcasting to {len(tasks)} agents: {broadcast_message}')
		return tasks

	async def exec_async(self, task):
		"""Each agent processes the broadcast request independently"""
		agent_name = task['agent']
		message = task['message']
		agent_config = task['agent_config']

		debug(f'[{agent_name.upper()}] Received broadcast, responding...')

		prompt = f"""{agent_config}

You have received a request from a colleague:
{message}

Respond briefly and directly to this request. Be concise.
"""

		# Run sync function in executor
		loop = asyncio.get_event_loop()
		response = await loop.run_in_executor(None, lambda: call_llm(prompt))

		return {
			'agent': agent_name,
			'response': response
		}

	async def post_async(self, shared, prep_res, exec_res_list):
		"""Compile all responses and return to requester"""
		requester = shared["requester_agent"]

		# Log the broadcast action
		shared["conversation_history"].append({
			'agent': requester,
			'action': 'broadcast',
			'summary': f"Broadcast to {len(exec_res_list)} team members",
			'data': exec_res_list
		})

		# Compile responses
		responses_text = "\n\n".join([
			f"[{r['agent'].upper()}] Response:\n{r['response']}"
			for r in exec_res_list
		])

		# Update task with all responses
		shared["current_task"] = f"Broadcast responses received:\n\n{responses_text}\n\nOriginal request: {shared['initial_message']}"
		shared["current_agent"] = requester

		debug(f'All broadcast responses collected, returning to {requester}')

		# Route back to the requester
		return requester

class RouteToColleagueNode(AsyncNode):
	"""Route task to ONE specific colleague"""
	async def exec_async(self, prep_res):
		return None

	async def post_async(self, shared, prep_res, exec_res):
		decision = shared["current_decision"]
		colleague = decision["colleague"]
		message = decision["delegation_message"]

		agent = shared["current_agent"]
		debug(f'[{agent.upper()}] Delegating to {colleague}: {message}')

		shared["conversation_history"].append({
			'agent': agent,
			'action': f'delegate_to_{colleague}',
			'summary': message,
			'data': None
		})

		# Switch to the colleague
		shared["current_agent"] = colleague
		shared["current_task"] = message

		return colleague

class FinalAnswerNode(AsyncNode):
	"""Extract and display final answer"""
	async def prep_async(self, shared):
		return shared["current_decision"].get("answer", "No answer provided")

	async def exec_async(self, answer):
		return answer

	async def post_async(self, shared, prep_res, exec_res):
		shared["final_answer"] = exec_res
		agent = shared["current_agent"]

		shared["conversation_history"].append({
			'agent': agent,
			'action': 'answer',
			'summary': f"Provided final answer",
			'data': exec_res
		})

		debug(f'[{agent.upper()}] Final answer provided')
		return "done"

class DisplayResult(AsyncNode):
	"""Display the final result"""
	async def exec_async(self, prep_res):
		return None

	async def post_async(self, shared, prep_res, exec_res):
		print("\n" + "="*60)
		print("FINAL ANSWER:")
		print("="*60)
		print(shared["final_answer"])
		print("\n" + "="*60)
		print(f"CONVERSATION SUMMARY ({len(shared['conversation_history'])} steps):")
		print("="*60)
		for i, step in enumerate(shared['conversation_history'], 1):
			print(f"{i}. [{step['agent'].upper()}] {step['action']}: {step['summary']}")
		print("="*60)
		return "default"

# Create nodes
get_input = GetUserInput()

# Agent decision nodes (one per agent)
cto_decide = AgentDecisionNode('cto')
dev_decide = AgentDecisionNode('lead_developer')
qa_decide = AgentDecisionNode('qa_lead')
sec_decide = AgentDecisionNode('secretary')

# Action nodes (shared by all agents)
search_web = SearchWebNode()
call_llm_node = CallLLMNode()
broadcast = BroadcastToAllNode()
route = RouteToColleagueNode()
final_answer = FinalAnswerNode()
display = DisplayResult()

# Wire up the flow
# Start with user input
get_input >> sec_decide

# Secretary decisions
sec_decide - "search" >> search_web
sec_decide - "llm" >> call_llm_node
sec_decide - "broadcast" >> broadcast
sec_decide - "colleague" >> route
sec_decide - "answer" >> final_answer

# CTO decisions
cto_decide - "search" >> search_web
cto_decide - "llm" >> call_llm_node
cto_decide - "broadcast" >> broadcast
cto_decide - "colleague" >> route
cto_decide - "answer" >> final_answer

# Lead Developer decisions
dev_decide - "search" >> search_web
dev_decide - "llm" >> call_llm_node
dev_decide - "broadcast" >> broadcast
dev_decide - "colleague" >> route
dev_decide - "answer" >> final_answer

# QA Lead decisions
qa_decide - "search" >> search_web
qa_decide - "llm" >> call_llm_node
qa_decide - "broadcast" >> broadcast
qa_decide - "colleague" >> route
qa_decide - "answer" >> final_answer

# Action nodes can route back to any agent
search_web - "secretary" >> sec_decide
search_web - "cto" >> cto_decide
search_web - "lead_developer" >> dev_decide
search_web - "qa_lead" >> qa_decide

call_llm_node - "secretary" >> sec_decide
call_llm_node - "cto" >> cto_decide
call_llm_node - "lead_developer" >> dev_decide
call_llm_node - "qa_lead" >> qa_decide

# Broadcast can return to any agent
broadcast - "secretary" >> sec_decide
broadcast - "cto" >> cto_decide
broadcast - "lead_developer" >> dev_decide
broadcast - "qa_lead" >> qa_decide

# Routing to colleagues
route - "cto" >> cto_decide
route - "lead_developer" >> dev_decide
route - "qa_lead" >> qa_decide
route - "secretary" >> sec_decide

# Final answer leads to display
final_answer - "done" >> display

# Create and run async flow
async def main():
	flow = AsyncFlow(start=get_input)
	shared = {}
	await flow.run_async(shared)

if __name__ == "__main__":
	asyncio.run(main())
