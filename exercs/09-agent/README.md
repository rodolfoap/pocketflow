# Web Search Q&A with PocketFlow

A simple question-answering application using PocketFlow that searches the web, crawls results, and uses GPT-4o to provide detailed answers.

## Features

- Interactive web search with DuckDuckGo
- Automatic crawling and extraction of page content
- AI-powered summarization using OpenAI's GPT-4o
- Retry mechanisms for robust API calls
- Clean separation of concerns using PocketFlow nodes

## Run It

1. Make sure your OpenAI API key is set:
    ```bash
    export OPENAI_API_KEY="your-api-key-here"
    ```

2. Install requirements and run the application:
    ```bash
    pip install -r requirements.txt
    python main.py
    ```

3. Enter your question when prompted

## How It Works

```mermaid
flowchart LR
    input[GetUserInput] --> search[SearchWeb]
    search --> summarize[Summarize]
```

The application uses three nodes:

1. **GetUserInput**: Prompts the user for a question
2. **SearchWeb**: Searches DuckDuckGo and crawls the top 3 results (with retry on failure)
3. **Summarize**: Uses GPT-4o to analyze the crawled content and answer the question (with retry on failure)

Each node follows PocketFlow best practices:
- `prep()`: Reads data from the shared store
- `exec()`: Performs computation without accessing shared
- `post()`: Writes results back to shared store

## Files

- [`main.py`](./main.py): Main flow with GetUserInput, SearchWeb, and Summarize nodes
- [`tools_llm.py`](./tools_llm.py): OpenAI API wrapper
- [`tools_websearch.py`](./tools_websearch.py): DuckDuckGo search and web scraping utilities
- [`tools_debug.py`](./tools_debug.py): Debug logging utility