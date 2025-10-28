from pocketflow import Node, Flow

class ChatNode(Node):
    def prep(self, shared):
        print('\nPREP', '='*71)
        user_input = int(input("Give me a number:"))
        if user_input == 0: return None

        if 'values' not in shared: 
            # Initializes arrays
            shared['values'] = [user_input]
            shared['pies'] = []
        else:
            shared['values'].append(user_input)

        return shared['values']

    def exec(self, values):
        # Just do calculations
        print('EXEC')
        if values is None: return None
        result = values[-1]*3.14
        print(values, '>', result)
        return result

    def post(self, shared, prep_res, exec_res):
        print('POST')
        if prep_res is None or exec_res is None:
            print("Goodbye!")
            return 'stop'
        print(f"exec(): {exec_res}")        
        shared["pies"].append(exec_res)
        print(f"shared: {shared}")        
        return "continue"

# Create the flow with self-loop
chat_node = ChatNode()
chat_node - "continue" >> chat_node  # Loop back to continue conversation
chat_node - "stop"  # FIXME I still don't know how to solve this
flow = Flow(start=chat_node)

# Start the chat
shared = {}
flow.run(shared)
