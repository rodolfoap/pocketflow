import os
from openai import OpenAI

def call_llm(prompt, model="gpt-4o-mini"):
    """Call OpenAI LLM with a prompt."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def search_web(query):
    """Simple web search using DuckDuckGo."""
    try:
        from dddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=7))
            # Format results as readable text
            formatted = []
            for r in results:
                formatted.append(f"Title: {r['title']}\n{r['body']}\nURL: {r['href']}")
            print('QUERY:', query)
            print('FORMATTED:', formatted)
            return "\n\n".join(formatted)
    except Exception as e:
        return f"Search failed: {str(e)}"

def send_message(target, message):
    """
    Send a message to a colleague.

    This is a placeholder - in a real system, this would:
    - Send an email
    - Post to Slack/Teams
    - Create a ticket

    For now, it just prints the message.
    """
    print(f"\n{'='*60}")
    print(f"📧 MESSAGE TO: {target}")
    print(f"{'='*60}")
    print(message)
    print(f"{'='*60}\n")
    return f"Message sent to {target}"

if __name__ == "__main__":
    # Test the utilities
    print("Testing LLM...")
    response = call_llm("Say 'Hello, I am ready to assist!'")
    print(f"✓ LLM: {response}\n")

    print("Testing web search...")
    results = search_web("Python programming")
    print(f"✓ Search results:\n{results[:200]}...\n")

    print("Testing message sending...")
    result = send_message("John Doe", "Can you review the quarterly report?")
    print(f"✓ {result}")
