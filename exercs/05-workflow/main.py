import sys, json
from pocketflow import Flow
from nodes import GenerateOutline, WriteSimpleContent, ApplyStyle

def create_article_flow():
    outline_node = GenerateOutline()
    write_node = WriteSimpleContent()
    style_node = ApplyStyle()
    outline_node >> write_node >> style_node
    flow = Flow(start=outline_node)
    return flow

def run_flow(topic="AI Safety"):
    shared = {"topic": topic}
    print(f"\n=== Starting Article Workflow on Topic: {topic} ===\n")
    # Run the flow
    flow = create_article_flow()
    flow.run(shared)
    print(json.dumps(shared, indent=8))
    return shared

topic = "AI Safety"  # Default topic
if len(sys.argv) > 1: topic = " ".join(sys.argv[1:])
run_flow(topic)