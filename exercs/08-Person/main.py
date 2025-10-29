import sys
from flow import create_secretary_flow

def main():
    """Run the intelligent secretary agent with natural language requests."""

    # Get user request from command line or use default
    if len(sys.argv) > 1:
        user_request = " ".join(sys.argv[1:])
    else:
        # Default test request
        user_request = "Search for Immanuel Kant's biography and make me a synthesis in two paragraphs"

    # Create the flow
    flow = create_secretary_flow()

    # Prepare shared store with just the user request
    shared = {
        "user_request": user_request,
        "context": "No actions taken yet."
    }

    # Run the secretary agent
    print("="*60)
    print("🤖 INTELLIGENT SECRETARY ASSISTANT")
    print("="*60)
    print(f"\n📝 Your request:\n{user_request}\n")
    print("="*60)

    flow.run(shared)

    # Display the final result if available
    print("\n" + "="*60)
    print("📊 FINAL RESULT")
    print("="*60)

    if "final_result" in shared:
        print(f"\n{shared['final_result']}\n")
    else:
        print("\nTask completed (no document generated)\n")

    print("="*60)

if __name__ == "__main__":
    main()
