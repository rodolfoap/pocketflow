from pocketflow import BatchNode, Flow
import random

class ChatNode(BatchNode):
    def prep(self, shared):
        print('\nPREP', '='*71)
        length = input("Size of the list:")
        if length == 0: return None
        array = [random.random() for _ in range(int(length))]
        print(array)
        return array

    def exec(self, values):
        # Runs once per element
        print('EXEC ---')
        if values is None: return None
        print(values, values * 2)
        return values * 2

    def post(self, shared, prep_res, exec_res):
        print('POST ---')
        if prep_res is None or exec_res is None:
            print("Goodbye!")
            return 'stop'
        print(f"exec(): {exec_res}")        
        return "continue"

# Create the flow with self-loop
chat_node = ChatNode()
chat_node - "continue" >> chat_node  # Loop back to continue conversation
chat_node - "stop"  # FIXME I still don't know how to solve this
flow = Flow(start=chat_node)

# Start the chat
shared = {}
flow.run(shared)
