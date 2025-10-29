from pocketflow import Flow
from nodes import DecideAction, SearchWeb, AnswerQuestion

def create_agent_flow():
    decide = DecideAction()
    search = SearchWeb()
    answer = AnswerQuestion()
    decide - "search" >> search
    decide - "answer" >> answer
    search - "decide" >> decide
    return Flow(start=decide) 