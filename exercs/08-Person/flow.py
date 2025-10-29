from pocketflow import Flow
from nodes import DecideAction, SearchWeb, SynthesizeDocument, SendMessage

def create_secretary_flow():
    """
    Create an intelligent secretary agent flow.

    Flow pattern:
    - DecideAction analyzes the request and decides what to do
    - Each action node loops back to DecideAction
    - DecideAction returns "done" when complete
    """
    # Create nodes
    decide = DecideAction()
    search = SearchWeb()
    synthesize = SynthesizeDocument()
    message = SendMessage()

    # Connect the flow
    decide - "search" >> search
    decide - "synthesize" >> synthesize
    decide - "message" >> message
    # When done, the flow ends naturally (no transition)

    # All action nodes loop back to decide
    search - "decide" >> decide
    synthesize - "decide" >> decide
    message - "decide" >> decide

    # Create and return the flow starting with decision
    return Flow(start=decide)
