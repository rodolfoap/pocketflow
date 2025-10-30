from pocketflow import Flow, Node
from tools_llm import call_llm
from tools_websearch import websearch
from tools_debug import debug

class NoOp(Node): # Does nothing
	pass

class GetUserInput(Node):
	def prep(self, shared):
		return None

	def exec(self, prep_res):
		#return "Bitcoin price?"
		return input("\nQuestion: ")

	def post(self, shared, prep_res, exec_res):
		shared["query"] = exec_res
		return "default"

class SearchWeb(Node):
	def __init__(self):
		super().__init__(max_retries=3, wait=2)

	def prep(self, shared):
		return shared["query"]

	def exec(self, query):
		debug('Web search...')
		# raise Exception('Testing error!')
		return websearch(query, crawl=True)

	def exec_fallback(self, query, error):
		debug(f'Web search failed: {error}')
		return []

	def post(self, shared, prep_res, exec_res):
		if len(exec_res) > 0:
			shared["search_results"] = "\n\n".join(item["text"] for item in exec_res)
			return "default"
		return "abort"

class Summarize(Node):
	def __init__(self):
		super().__init__(max_retries=2, wait=5)

	def prep(self, shared):
		return shared["query"], shared["search_results"]

	def exec(self, prep_res):
		debug('LLM synthesis...')
		query, search_results = prep_res
		prompt = f'Read the text below and answer in as much detail as possible: {query}\n---\n{search_results}'
		return call_llm(prompt)

	def post(self, shared, prep_res, exec_res):
		shared["summary"] = exec_res
		return "default"

get_input = GetUserInput()
search = SearchWeb()
summarize = Summarize()
noop = NoOp()

get_input >> search >> summarize
search - "abort" >> noop

flow = Flow(start=get_input)
shared = {}
flow.run(shared)

if "summary" in shared: print(shared["summary"])
