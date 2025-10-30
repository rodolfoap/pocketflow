from pocketflow import Flow, Node
from tools_llm import call_llm
from tools_websearch import websearch

class SearchWeb(Node):
	def prep(self, shared):
		shared["query"] = input("\nQuestion: ")
		return shared["query"]

	def exec(self, prep_res):
		exec_res = websearch(prep_res, crawl=True)
		return exec_res

	def post(self, shared, prep_res, exec_res):
		shared["response"] = ''
		for item in exec_res: shared["response"]+=f'{item["text"]}\n\n'
		return None

class Summarize(Node):
	def prep(self, shared):
		return shared["response"]

	def exec(self, prep_res):
		query=shared["query"]
		prompt=f'Read the text below and answer in as much detail as possible: {query}\n---\n{prep_res}'
		exec_res = call_llm(prompt)
		return exec_res

	def post(self, shared, prep_res, exec_res):
		shared["summary"] = exec_res
		return "default"

load_data = SearchWeb()
summarize = Summarize()
load_data >> summarize
flow = Flow(start=load_data)
shared = {}
flow.run(shared)
print(shared["summary"])
