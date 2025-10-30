from pocketflow import Flow, Node
from tools_llm import call_llm
from tools_websearch import websearch
from tools_debug import debug
import yaml

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

class GetUserInput(Node):
	"""Get initial user message and assign to first agent"""
	def exec(self, prep_res):
		return input("\n[User] Message: ")

	def post(self, shared, prep_res, exec_res):
		shared["initial_message"] = exec_res
		shared["current_task"] = exec_res
		shared["current_agent"] = "secretary"  # Start with secretary
		shared["conversation_history"] = []
		shared["final_answer"] = None
		shared["max_hops"] = 15
		shared["current_hop"] = 0
		return "default"

class AgentDecisionNode(Node):
	"""Agent decides: search web, call LLM, ask colleague, or answer"""
	def __init__(self, agent_name):
		super().__init__(max_retries=2, wait=3)
		self.agent_name = agent_name

	def prep(self, shared):
		return {
			'task': shared["current_task"],
			'history': shared["conversation_history"],
			'agent_config': AGENTS[self.agent_name]
		}

	def exec(self, prep_res):
		debug(f'[{self.agent_name.upper()}] Thinking...')

		prompt = f"""{prep_res['agent_config']}

CONVERSATION HISTORY:
{self._format_history(prep_res['history'])}

CURRENT TASK ASSIGNED TO YOU:
{prep_res['task']}

INSTRUCTIONS:
Decide what action to take. You have 4 options:
1. search - Search the web for information
2. llm - Write a prompt and query an LLM for analysis/generation
3. colleague - Ask a colleague (cto, lead_developer, qa_lead, secretary) for help
4. answer - Provide the final answer to complete the task

Respond ONLY with valid YAML in this exact format:
```yaml
action: search|llm|colleague|answer
reasoning: brief explanation of your decision
query: the search query (if action=search)
prompt: the LLM prompt (if action=llm)
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

	def post(self, shared, prep_res, exec_res):
		action = exec_res['action']
		shared["current_decision"] = exec_res

		# Check hop limit
		shared["current_hop"] += 1
		if shared["current_hop"] >= shared["max_hops"]:
			debug(f"Max hops reached, forcing answer")
			return "answer"

		debug(f'[{self.agent_name.upper()}] Decision: {action} - {exec_res.get("reasoning", "")}')
		return action

class SearchWebNode(Node):
	"""Perform web search"""
	def __init__(self):
		super().__init__(max_retries=2, wait=2)

	def prep(self, shared):
		query = shared["current_decision"]["query"]
		return query

	def exec(self, query):
		debug(f'Searching web for: {query}')
		results = websearch(query, max_results=3, crawl=False)
		return results

	def exec_fallback(self, query, error):
		debug(f'Web search failed: {error}')
		return []

	def post(self, shared, prep_res, exec_res):
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

class CallLLMNode(Node):
	"""Call LLM with custom prompt"""
	def __init__(self):
		super().__init__(max_retries=2, wait=3)

	def prep(self, shared):
		prompt = shared["current_decision"]["prompt"]
		return prompt

	def exec(self, prompt):
		debug(f'Calling LLM...')
		return call_llm(prompt)

	def post(self, shared, prep_res, exec_res):
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

class RouteToColleagueNode(Node):
	"""Route task to a colleague"""
	def exec(self, prep_res):
		return None

	def post(self, shared, prep_res, exec_res):
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

class FinalAnswerNode(Node):
	"""Extract and display final answer"""
	def prep(self, shared):
		return shared["current_decision"].get("answer", "No answer provided")

	def exec(self, answer):
		return answer

	def post(self, shared, prep_res, exec_res):
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

class DisplayResult(Node):
	"""Display the final result"""
	def exec(self, prep_res):
		return None

	def post(self, shared, prep_res, exec_res):
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
route = RouteToColleagueNode()
final_answer = FinalAnswerNode()
display = DisplayResult()

# Wire up the flow
# Start with user input
get_input >> sec_decide

# Secretary decisions
sec_decide - "search" >> search_web
sec_decide - "llm" >> call_llm_node
sec_decide - "colleague" >> route
sec_decide - "answer" >> final_answer

# CTO decisions
cto_decide - "search" >> search_web
cto_decide - "llm" >> call_llm_node
cto_decide - "colleague" >> route
cto_decide - "answer" >> final_answer

# Lead Developer decisions
dev_decide - "search" >> search_web
dev_decide - "llm" >> call_llm_node
dev_decide - "colleague" >> route
dev_decide - "answer" >> final_answer

# QA Lead decisions
qa_decide - "search" >> search_web
qa_decide - "llm" >> call_llm_node
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

# Routing to colleagues
route - "cto" >> cto_decide
route - "lead_developer" >> dev_decide
route - "qa_lead" >> qa_decide
route - "secretary" >> sec_decide

# Final answer leads to display
final_answer - "done" >> display

# Create and run flow
flow = Flow(start=get_input)
shared = {}
flow.run(shared)
