from pocketflow import Node
from utils import call_llm, search_web, send_message
import yaml

class DecideAction(Node):
    """
    Intelligent decision node that analyzes the user request and decides what action to take.

    Actions:
    - search: Search the web for information
    - synthesize: Create a document or summary
    - message: Send a message to a colleague
    - done: Task is complete
    """

    def prep(self, shared):
        """Get the user request and current context."""
        # Initialize context if not present
        if "context" not in shared:
            shared["context"] = "No actions taken yet."

        # Get the original user request
        user_request = shared["user_request"]
        context = shared["context"]

        return user_request, context

    def exec(self, inputs):
        """Analyze the request and decide what action to take next."""
        user_request, context = inputs

        print(f"\n🤔 Analyzing what to do next...")

        # Create a prompt for the LLM to decide the next action
        prompt = f"""
You are an intelligent secretary assistant analyzing what action to take.

### USER REQUEST
{user_request}

### CONTEXT (what has been done so far)
{context}

### AVAILABLE ACTIONS
[1] search
  Description: Search the web for information
  Parameters:
    - query (str): What to search for

[2] synthesize
  Description: Create a document, summary, or synthesis from gathered information
  Parameters:
    - instruction (str): What to synthesize and how (e.g., "2 paragraphs", "professional memo")

[3] message
  Description: Send a message to a colleague
  Parameters:
    - target (str): Person to contact
    - question (str): What to ask them

[4] done
  Description: The request has been fully completed
  Parameters: none

### YOUR TASK
Decide the NEXT action to take based on the user request and context.

Return your response in this YAML format:

```yaml
thinking: |
    Your step-by-step reasoning about what to do next
action: search OR synthesize OR message OR done
reason: Why you chose this action
query: <if action is search, specify the search query>
instruction: <if action is synthesize, specify what to create and how>
target: <if action is message, specify the person>
question: <if action is message, specify what to ask>
```

IMPORTANT: Choose the simplest action that makes progress toward completing the request.
"""

        # Call the LLM to make a decision
        response = call_llm(prompt)

        # Parse the YAML response
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        decision = yaml.safe_load(yaml_str)

        return decision

    def post(self, shared, prep_res, exec_res):
        """Save the decision and return the action to take."""
        action = exec_res["action"]

        # Save the decision details for the next node
        if action == "search":
            shared["search_query"] = exec_res.get("query", "")
            print(f"🔍 Decision: Search for '{shared['search_query']}'")
        elif action == "synthesize":
            shared["synthesize_instruction"] = exec_res.get("instruction", "")
            print(f"📝 Decision: Synthesize - {shared['synthesize_instruction']}")
        elif action == "message":
            shared["message_target"] = exec_res.get("target", "")
            shared["message_question"] = exec_res.get("question", "")
            print(f"💌 Decision: Message {shared['message_target']}")
        else:
            print(f"✅ Decision: Task is complete!")

        # Return the action which determines the next node
        return action


class SearchWeb(Node):
    """Search the web and add results to context."""

    def prep(self, shared):
        """Get the search query from shared store."""
        return shared["search_query"]

    def exec(self, query):
        """Perform the web search."""
        print(f"🌐 Searching the web...")
        results = search_web(query)
        return results

    def post(self, shared, prep_res, exec_res):
        """Add search results to context and go back to decision node."""
        # Update the context with search results
        previous_context = shared.get("context", "")
        shared["context"] = (
            previous_context +
            f"\n\n[SEARCH COMPLETED]\n"
            f"Query: {prep_res}\n"
            f"Results:\n{exec_res}"
        )

        print(f"✓ Search completed, results added to context")

        # Go back to decision node
        return "decide"


class SynthesizeDocument(Node):
    """Create a synthesis, summary, or document from the gathered information."""

    def prep(self, shared):
        """Get the synthesis instruction and context."""
        instruction = shared["synthesize_instruction"]
        context = shared.get("context", "No information available")
        user_request = shared["user_request"]

        return instruction, context, user_request

    def exec(self, inputs):
        """Create the synthesis using the LLM."""
        instruction, context, user_request = inputs

        print(f"✍️ Creating synthesis...")

        prompt = f"""
You are a professional secretary creating a document.

### ORIGINAL REQUEST
{user_request}

### INSTRUCTION
{instruction}

### AVAILABLE INFORMATION
{context}

### YOUR TASK
Create the requested synthesis/document/summary based on the instruction and available information.
Be concise, professional, and well-structured.

Your synthesis:
"""

        result = call_llm(prompt)
        return result

    def post(self, shared, prep_res, exec_res):
        """Save the synthesis and go back to decision node."""
        # Update context with the synthesis
        previous_context = shared.get("context", "")
        shared["context"] = (
            previous_context +
            f"\n\n[SYNTHESIS COMPLETED]\n"
            f"Result:\n{exec_res}"
        )

        # Also save the final result for easy access
        shared["final_result"] = exec_res

        print(f"✓ Synthesis completed")

        # Go back to decision node
        return "decide"


class SendMessage(Node):
    """Send a message to a colleague."""

    def prep(self, shared):
        """Get the message details from shared store."""
        target = shared["message_target"]
        question = shared["message_question"]
        return target, question

    def exec(self, inputs):
        """Create and send the message."""
        target, question = inputs

        print(f"💌 Composing message...")

        # Format a professional message
        prompt = f"""
You are a professional secretary. Write a brief, polite message asking:
{question}

Keep it professional and concise (2-3 sentences max).
"""
        message_text = call_llm(prompt)

        # Send the message
        send_message(target, message_text)

        return f"Message sent to {target}"

    def post(self, shared, prep_res, exec_res):
        """Update context and go back to decision node."""
        target, question = prep_res

        # Update context
        previous_context = shared.get("context", "")
        shared["context"] = (
            previous_context +
            f"\n\n[MESSAGE SENT]\n"
            f"To: {target}\n"
            f"About: {question}"
        )

        print(f"✓ Message sent successfully")

        # Go back to decision node
        return "decide"

