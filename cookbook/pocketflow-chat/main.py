from pocketflow import Node, Flow
from utils import call_llm

class ChatNode(Node):
    def prep(self, shared):
        # Get the required data from the repository
        if "messages" not in shared:
            shared["messages"] = []
            print("Welcome to the chat! Type 'exit' to end the conversation.")
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit': return None
        shared["messages"].append({"role": "user", "content": user_input})
        return shared["messages"]

    def exec(self, messages):
        # `shared` is not visible here, only `shared['messages']`
        if messages is None: return None
        response = call_llm(messages)
        return response

    def post(self, shared, prep_res, exec_res):
        # If there are no MESSAGES or no EXEC RESPONSE, end
        if prep_res is None or exec_res is None:
            print("\nGoodbye!")
            return None  # End the conversation
        print(f"\nAssistant: {exec_res}")        
        shared["messages"].append({"role": "assistant", "content": exec_res})
        # for m in shared["messages"]: print(f'> {m}')
        return "continue"

# Create the flow with self-loop
chat_node = ChatNode()
chat_node - "continue" >> chat_node  # Loop back to continue conversation
flow = Flow(start=chat_node)

# Start the chat
shared = {}
flow.run(shared)
