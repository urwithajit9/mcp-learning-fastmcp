# Building Agentic AI with MCP, FastMCP & Ollama
## A Complete Beginner-to-Advanced Tutorial

> **Based on real-world experience building and iterating a local agentic AI system.**
> This tutorial walks you through everything — from understanding what MCP is, to building production-worthy AI agents that call real tools, handle errors gracefully, and integrate into larger projects.

---

## Table of Contents

1. [What is MCP and Why Does It Matter?](#1-what-is-mcp-and-why-does-it-matter)
2. [How the System Works — Architecture Deep Dive](#2-how-the-system-works--architecture-deep-dive)
3. [Setting Up Your Environment](#3-setting-up-your-environment)
4. [Your First MCP Server — Toy Tools](#4-your-first-mcp-server--toy-tools)
5. [Your First MCP Client — Talking to Ollama](#5-your-first-mcp-client--talking-to-ollama)
6. [Running It End-to-End — What to Expect](#6-running-it-end-to-end--what-to-expect)
7. [Understanding Tool Calling — How LLMs Decide](#7-understanding-tool-calling--how-llms-decide)
8. [Intermediate: Real-World Tool — Weather API](#8-intermediate-real-world-tool--weather-api)
9. [Lessons Learned from Real Outputs](#9-lessons-learned-from-real-outputs)
10. [Advanced: Three Complete Real-World Use Cases](#10-advanced-three-complete-real-world-use-cases)
    - [Use Case 1: Personal Finance Assistant](#use-case-1-personal-finance-assistant)
    - [Use Case 2: DevOps Health Monitor](#use-case-2-devops-health-monitor)
    - [Use Case 3: Research Assistant with Web + File Tools](#use-case-3-research-assistant-with-web--file-tools)
11. [How a Real Project Is Structured](#11-how-a-real-project-is-structured)
12. [Choosing the Right Ollama Model](#12-choosing-the-right-ollama-model)
13. [Debugging and Troubleshooting](#13-debugging-and-troubleshooting)
14. [What's Next — Going Beyond](#14-whats-next--going-beyond)

---

## 1. What is MCP and Why Does It Matter?

### The Core Problem

Large Language Models (LLMs) like those running in Ollama are powerful text generators, but they have a fundamental limitation: **they are stateless and sealed**. They know only what was in their training data. They cannot browse the internet, read your files, call an API, or take an action in the world — at least not on their own.

To give LLMs real-world capabilities, developers have historically built custom code that stuffs API results into prompts, parses output with fragile regex, and glues everything together with bespoke logic. This works, but it doesn't scale. Every new tool requires re-writing integration code. Every new LLM needs its own adapter.

**Model Context Protocol (MCP)** solves this by providing a **standardized contract** between an LLM client and any external tool or data source.

### What MCP Actually Is

MCP (created by Anthropic) is an open protocol that defines:

- How tools are **described** (name, parameters, types, description)
- How tool **calls are requested** (by the LLM)
- How tool **results are returned** (structured, typed responses)
- How these exchanges happen over a **transport layer** (HTTP, stdio)

Think of it like USB for AI tools. Before USB, every peripheral needed its own connector. After USB, any device plugs into any computer. MCP is the USB port for AI capabilities.

### FastMCP — The Easy Button

**FastMCP** is a Python library that implements the MCP server specification with minimal boilerplate. Instead of writing protocol-level JSON, you just decorate a Python function:

```python
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
```

FastMCP handles serialization, type validation, schema generation, and the HTTP server — all automatically.

### Ollama — Local LLMs Without the Cloud

**Ollama** lets you run models like Llama 3.2, Mistral, and Qwen on your own machine. No API keys, no per-token costs, no data leaving your computer. The Ollama Python library gives you a simple interface to these models, including support for **tool calling** — the mechanism where the model requests a function be executed.

### Putting It Together

MCP + FastMCP + Ollama gives you a **fully local, fully private, extensible agentic AI system**. The LLM runs on your GPU/CPU, the tools run in your Python environment, and you control everything.

---

## 2. How the System Works — Architecture Deep Dive

Before writing a single line of code, it's essential to understand the data flow. Many bugs come from misunderstanding what happens at each step.

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR MACHINE                                │
│                                                                 │
│  ┌──────────────┐    ┌───────────────────────┐    ┌──────────┐  │
│  │              │    │                       │    │          │  │
│  │  Ollama LLM  │◄──►│   Python Client       │◄──►│  FastMCP │  │
│  │  (llama3.2)  │    │   (Orchestrator)      │    │  Server  │  │
│  │              │    │                       │    │  :8080   │  │
│  └──────────────┘    └───────────────────────┘    └──────────┘  │
│                                                       │          │
│                                               ┌───────┴──────┐  │
│                                               │    Tools     │  │
│                                               │  add()       │  │
│                                               │  greet()     │  │
│                                               │  get_weather()│ │
│                                               │  ...         │  │
│                                               └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### The Step-by-Step Flow

**Step 1 — Tool Discovery**
At startup, the Python client connects to the FastMCP server and fetches a list of all available tools. Each tool comes with its name, description, and JSON schema for parameters. The client converts these into Ollama's tool format.

**Step 2 — User Query**
The user sends a message (e.g., "What's the weather in Seoul for the next 10 days?"). The client packages this into a chat message along with the full list of available tools.

**Step 3 — LLM Decision**
Ollama receives the message + tools and returns one of two things:
- A **direct text response** (if it can answer without tools)
- A **tool call request** (structured JSON specifying which tool to call and with what arguments)

**Step 4 — Tool Execution**
The client reads the tool call request, connects back to FastMCP, and executes the tool with the provided arguments. The tool runs, and its result is returned.

**Step 5 — Result Injection**
The tool result is added to the conversation history as a `"role": "tool"` message.

**Step 6 — Final Response**
The full conversation history (user message + tool call + tool result) is sent back to Ollama, which now generates a natural language response incorporating the real data.

### The Message History

Understanding the message history structure is critical. Here's what gets built up:

```python
messages = [
    # Step 2: Original user query
    {"role": "user", "content": "What's the weather in Seoul for 10 days?"},

    # Step 3: LLM's tool call request (returned by Ollama)
    {"role": "assistant", "tool_calls": [{"function": {"name": "get_weather", "arguments": {"city": "Seoul", "forecast_days": 10}}}]},

    # Step 5: Tool execution result
    {"role": "tool", "content": '{"city": "Seoul", "forecast": [...]}'},

    # Step 6: Final response from LLM (generated fresh)
    # {"role": "assistant", "content": "Here is Seoul's 10-day forecast..."}
]
```

---

## 3. Setting Up Your Environment

### Prerequisites

- Python 3.11 or higher (`python --version`)
- pip (comes with Python)
- 8GB+ RAM (for running 3B models; 16GB+ for 7B+)
- A terminal/command prompt

### Step 1: Install Ollama

Visit [https://ollama.ai/download](https://ollama.ai/download) and install for your OS.

After installation, verify it works:

```bash
ollama --version
```

### Step 2: Pull a Tool-Compatible Model

Not all models support tool calling. Start with `llama3.2` (3B parameters, fast, good at tools):

```bash
ollama pull llama3.2
```

This downloads ~2GB. While waiting, continue with the next steps.

### Step 3: Create a Project and Virtual Environment

```bash
# Create project directory
mkdir mcp-ai-agent
cd mcp-ai-agent

# Create isolated Python environment
python -m venv myenv

# Activate it
source myenv/bin/activate        # macOS/Linux
# myenv\Scripts\activate         # Windows
```

Your prompt should now show `(myenv)` at the start.

### Step 4: Install Dependencies

```bash
pip install fastmcp ollama requests httpx
```

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP server framework |
| `ollama` | Python client for Ollama API |
| `requests` | HTTP requests (for some tool examples) |
| `httpx` | Async HTTP client (used in async tools) |

### Step 5: Verify Ollama is Running

```bash
ollama serve   # Start the Ollama service (if not already running as a daemon)
```

In another terminal:
```bash
curl http://localhost:11434/api/tags
# Should return a JSON list of your downloaded models
```

---

## 4. Your First MCP Server — Toy Tools

Let's build the simplest possible MCP server with two tools: one that adds numbers, one that greets someone. These "toy" examples are intentional — they let you focus on the mechanics of MCP without worrying about what the tools actually do.

Create `mcp_server.py`:

```python
# mcp_server.py
from fastmcp import FastMCP

# Create the MCP server instance with a name
mcp = FastMCP("MyFirstAgent 🚀")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


@mcp.tool
def greet(name: str) -> str:
    """Greet a person by name. Returns a friendly greeting message."""
    return f"Hello, {name}! Welcome aboard!"


@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

### What's Happening Here

**`FastMCP("MyFirstAgent 🚀")`** — Creates a server instance with a display name. The name is cosmetic but useful for logging.

**`@mcp.tool`** — This decorator does three things automatically:
1. Registers the function as an available MCP tool
2. Extracts the parameter names and types from Python type hints to build a JSON schema
3. Uses the docstring as the tool's description (which the LLM reads when deciding whether to use it)

**The docstring is critically important.** The LLM uses the description to decide *whether and when* to call a tool. A vague or missing description leads to missed tool calls or wrong tool selection.

### Start the Server

In Terminal 1:

```bash
python mcp_server.py
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

The server is now running and waiting for connections. Leave this terminal open.

### Testing the Server Directly (Optional)

Before connecting Ollama, you can verify the server works by listing its tools:

```python
# test_server.py - run this in a separate terminal
import asyncio
from fastmcp import Client as MCPClient

async def test():
    async with MCPClient("http://127.0.0.1:8080/mcp") as mcp:
        tools = await mcp.list_tools()
        for t in tools:
            print(f"Tool: {t.name}")
            print(f"  Description: {t.description}")
            print(f"  Schema: {t.inputSchema}")
            print()

asyncio.run(test())
```

---

## 5. Your First MCP Client — Talking to Ollama

The client is the "brain" of the system — it orchestrates everything. Create `client_ollama.py`:

```python
# client_ollama.py
import json
import sys
import asyncio
import ollama
from fastmcp import Client as MCPClient

# ── Configuration ────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2:latest"
MCP_SERVER_URL = "http://127.0.0.1:8080/mcp"


# ── Step 1: Tool Discovery ───────────────────────────────────────
async def load_mcp_tools() -> list:
    """Connect to FastMCP server and retrieve available tools in Ollama format."""
    try:
        async with MCPClient(MCP_SERVER_URL) as mcp:
            tools_list = await mcp.list_tools()

            # Convert MCP tool format → Ollama tool format
            ollama_tools = []
            for tool in tools_list:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                })
            return ollama_tools

    except Exception as e:
        print(f"❌ ERROR connecting to FastMCP server: {e}")
        print(f"   Make sure the server is running: python mcp_server.py")
        sys.exit(1)


# ── Step 4: Tool Execution ───────────────────────────────────────
async def execute_tool(tool_name: str, arguments: dict):
    """Execute a single tool on the FastMCP server and return its result."""
    try:
        async with MCPClient(MCP_SERVER_URL) as mcp:
            result = await mcp.call_tool(tool_name, arguments)
            return result
    except Exception as e:
        print(f"⚠️  ERROR executing tool '{tool_name}': {e}")
        return {"error": str(e)}


# ── Main Conversation Loop ───────────────────────────────────────
async def chat(user_message: str):
    """Run a single turn of the agentic conversation loop."""

    # Step 1: Load tools from MCP server
    print("🔧 Loading tools from MCP server...")
    tools = await load_mcp_tools()
    print(f"   Loaded {len(tools)} tools: {[t['function']['name'] for t in tools]}\n")

    print(f"👤 User: {user_message}\n")

    # Step 3: First LLM call — let it decide what to do
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
            stream=False,
        )
    except Exception as e:
        print(f"❌ ERROR calling Ollama: {e}")
        print(f"   Make sure Ollama is running and model '{OLLAMA_MODEL}' is available.")
        sys.exit(1)

    # Check if LLM decided to answer directly (no tools needed)
    if not response.get("message", {}).get("tool_calls"):
        print("🤖 LLM answered directly (no tools needed):")
        print(response["message"]["content"])
        return

    # Step 4+5: Handle tool calls
    messages = [
        {"role": "user", "content": user_message},
        response["message"],  # includes the tool_calls
    ]

    for tool_call in response["message"]["tool_calls"]:
        tool_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]

        # Arguments may come as a JSON string — parse if needed
        if isinstance(args, str):
            args = json.loads(args)

        print(f"🔨 Calling tool: {tool_name}")
        print(f"   Arguments: {args}")

        result = await execute_tool(tool_name, args)
        print(f"   Result: {result}\n")

        # Add the tool result to the conversation
        messages.append({
            "role": "tool",
            "content": (
                json.dumps(result) if isinstance(result, dict) else str(result)
            ),
        })

    # Step 6: Final LLM call with tool results in context
    final_response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
    )

    print("🤖 Final Response:")
    print(final_response["message"]["content"])


# ── Entry Point ──────────────────────────────────────────────────
if __name__ == "__main__":
    user_msg = "Please greet John and then add 150 + 75."
    asyncio.run(chat(user_msg))
```

### Run the Client

In Terminal 2 (with your virtual env active):

```bash
python client_ollama.py
```

---

## 6. Running It End-to-End — What to Expect

Here's the actual output from running the toy example:

```
🔧 Loading tools from MCP server...
   Loaded 2 tools: ['add', 'greet']

👤 User: Please greet John and then add 150 + 75.

🔨 Calling tool: greet
   Arguments: {'name': 'John'}
   Result: Hello, John! Welcome aboard!

🔨 Calling tool: add
   Arguments: {'a': 150, 'b': 75}
   Result: 225

🤖 Final Response:
Hello John! Welcome aboard! The sum of 150 and 75 is 225.
```

Notice that the LLM correctly:
1. Identified two separate things to do
2. Called two different tools in sequence
3. Incorporated both results into a single coherent response

---

## 7. Understanding Tool Calling — How LLMs Decide

This is one of the most important things to understand, and it's where most beginners get confused.

### The LLM Reads Your Docstrings

When Ollama receives a list of tools, each tool has a `description` field that comes directly from your Python docstring. The LLM reads these descriptions to determine:

- **Does this tool exist for what the user is asking?**
- **When should I call this tool vs. answer directly?**
- **Which tool should I call if multiple are available?**

**Bad docstring:**
```python
@mcp.tool
def greet(name: str) -> str:
    """Greet"""  # Too vague — model may not use this correctly
    return f"Hello, {name}!"
```

**Good docstring:**
```python
@mcp.tool
def greet(name: str) -> str:
    """
    Greet a person by their first name.
    Use this when the user asks you to greet, welcome, or say hello to someone.
    Returns a friendly welcome message.
    """
    return f"Hello, {name}! Welcome aboard!"
```

### Tool Selection Priority

From real-world testing (as seen in the outputs shared), when **two similar tools** are available (e.g., `predict_weather` and `get_weather`), the LLM tends to:

1. Call the **first one listed** if descriptions are similar
2. Follow instructions in the docstring about when to use it

The fix is **explicit priority language** in docstrings:

```python
@mcp.tool
def predict_weather(city: str, forecast_days: int = 1) -> dict:
    """
    Demo mock weather tool. ONLY supports 1-7 days.
    DO NOT use for real forecasts. For real weather data, use get_weather instead.
    """
    ...

@mcp.tool
def get_weather(city: str, forecast_days: int = 7) -> dict:
    """
    Get REAL weather forecast for a city (supports up to 16 days).
    USE THIS for all real-world weather queries. Prefers this over predict_weather.
    """
    ...
```

### Type Coercion Issues

A subtle but important issue from real outputs: Ollama sometimes passes arguments as **strings** even when the schema says `int` or `float`.

Observed in the real output:
```
Arguments: {'a': '150', 'b': '75'}  # These are strings, not ints!
```

FastMCP's Pydantic validation will usually coerce these correctly, but it's good practice to handle it defensively:

```python
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return int(a) + int(b)  # Explicit cast as defensive coding
```

### When Does the LLM NOT Call a Tool?

If the query can be answered from training knowledge and no tool seems applicable, the LLM will answer directly. Example:

- Query: *"What is 2 + 2?"* → LLM answers "4" directly (even if `add` is available)
- Query: *"Please use the add tool to compute 2 + 2"* → Now it calls `add`

You can force tool usage through prompt phrasing, but generally you want the LLM to decide naturally.

---

## 8. Intermediate: Real-World Tool — Weather API

Now let's replace the toy example with a real, useful tool that calls an external API. This section mirrors what was actually built and tested.

### The Weather Tool (Production Version)

```python
# mcp_server.py — extended with real weather

import httpx
from typing import Dict, Literal
from fastmcp import FastMCP

mcp = FastMCP("WeatherAgent 🌤️")


# ── Geocoding helper ─────────────────────────────────────────────
async def geocode_city(city: str):
    """Convert city name to latitude/longitude using Open-Meteo's free geocoding API."""
    url = "https://geocoding-api.open-meteo.com/v1/search"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={"name": city, "count": 1})
        data = response.json()

    if not data.get("results"):
        return None

    result = data["results"][0]
    return result["latitude"], result["longitude"], result.get("country", "Unknown")


# ── Weather tool ─────────────────────────────────────────────────
@mcp.tool
async def get_weather(city: str, forecast_days: int = 7) -> Dict:
    """
    Get REAL weather forecast for any city worldwide (up to 16 days).
    Uses the free Open-Meteo API — no API key required.
    Returns daily max and min temperatures in Celsius.
    Use this for any real-world weather question.

    Args:
        city: Name of the city (e.g., 'Seoul', 'London', 'New York')
        forecast_days: Number of days ahead (1-16, default 7)
    """
    if forecast_days < 1 or forecast_days > 16:
        return {"error": "forecast_days must be between 1 and 16"}

    # Geocode the city
    geo = await geocode_city(city)
    if not geo:
        return {"error": f"Could not find city '{city}'. Try a more specific name."}

    lat, lon, country = geo

    # Fetch forecast from Open-Meteo
    async with httpx.AsyncClient() as client:
        weather_response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": forecast_days,
            }
        )
        weather_data = weather_response.json()

    daily = weather_data.get("daily", {})
    forecast = [
        {
            "date": daily["time"][i],
            "temp_max_C": daily["temperature_2m_max"][i],
            "temp_min_C": daily["temperature_2m_min"][i],
        }
        for i in range(len(daily.get("time", [])))
    ]

    return {
        "city": city,
        "country": country,
        "forecast_days": forecast_days,
        "source": "Open-Meteo (free, no API key)",
        "forecast": forecast,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

### Key Points About Async Tools

Notice `async def get_weather(...)` — FastMCP fully supports `async` tools, which is important when your tool makes network requests. Without `async`, the server would block while waiting for the HTTP response, making it unresponsive to other requests.

### Testing the Weather Agent

Update `client_ollama.py` to ask a weather question:

```python
user_msg = "What's the weather forecast for Seoul, South Korea for the next 10 days?"
```

### Real Output (Reproduced from Actual Tests)

```
🔧 Loading tools from MCP server...
   Loaded 3 tools: ['add', 'greet', 'get_weather']

👤 User: Tell the current weather of Seoul, South Korea and next 10 days prediction

🔨 Calling tool: get_weather
   Arguments: {'city': 'Seoul', 'forecast_days': 10}
   Result: {"city":"Seoul","country":"South Korea","forecast_days":10,...}

🤖 Final Response:
Seoul, South Korea — 10-Day Forecast:
- Feb 19: High 4.6°C / Low -5.6°C
- Feb 20: High 11.1°C / Low -2.8°C
...
```

### Formatting Instructions in the Prompt

An important discovery from testing: **you can instruct the LLM how to format the tool results** directly in your query:

```python
user_msg = """
Tell the current weather of Seoul, South Korea for the next 10 days.
Format the output as a markdown table with emoji weather indicators.
Add a brief summary of the overall temperature trend.
"""
```

The LLM will respect this formatting request when composing its final response, even though the raw tool output is plain JSON.

---

## 9. Lessons Learned from Real Outputs

Based on the actual test outputs, here are the key insights:

### Lesson 1: Missing Tools Lead to Hallucination

When a tool the user expects isn't available, the LLM doesn't say "I can't do that." It tries to answer anyway — and hallucinates. In the real output, when there was no weather tool:

> *The LLM called `add(10, 20)` and `greet("Seoul")` — the closest tools it had — then made up weather information.*

**Solution:** Always provide the right tool, and test with edge-case queries to see what the model does when tools don't match.

### Lesson 2: Error Responses Must Be Informative

When a tool returns an error (like `forecast_days must be between 1 and 7`), the LLM reads that error and tries to help the user. If the error message is clear, the LLM gives good advice. If it's cryptic, the LLM is equally confused.

**Bad error:**
```python
return {"error": "invalid param"}
```

**Good error:**
```python
return {
    "error": "forecast_days must be between 1 and 16. You requested 30. Try 16 for the maximum.",
    "suggestion": "For extended forecasts, consider checking a specialized weather service."
}
```

### Lesson 3: Tool Order Matters (When Descriptions Are Ambiguous)

With two weather tools, the LLM chose `predict_weather` (the mock) over `get_weather` (real) because it appeared first in the list. The fix is either clear priority language in docstrings, or removing ambiguous tools.

### Lesson 4: Validate Arguments Defensively

The LLM may pass `'10'` (string) where you expect `10` (int). FastMCP + Pydantic handles this in most cases, but be aware of it.

### Lesson 5: The LLM Invents Data It Doesn't Have

In the weather output, the LLM added:
> *"February 19: Cloudy with a high temperature of 4.6°C"*

The word "Cloudy" was **invented** — the API only returned temperature, not conditions. The LLM filled in the gap. This is a feature (natural responses) and a bug (inaccurate data). Address it in the tool's description:

```python
"""
Returns ONLY temperature data (max/min per day).
Does NOT return weather conditions like 'cloudy' or 'rainy'.
Remind the user that condition descriptions are not available from this data source.
"""
```

---

## 10. Advanced: Three Complete Real-World Use Cases

Now let's build three complete, production-quality use cases using the same MCP + FastMCP + Ollama architecture.

---

### Use Case 1: Personal Finance Assistant

**Goal:** An AI assistant that can query your expenses, calculate summaries, convert currencies, and give spending advice — all locally, all private.

#### The MCP Server

```python
# finance_server.py
import json
from datetime import datetime, date
from typing import Dict, List, Optional
import httpx
from fastmcp import FastMCP

mcp = FastMCP("FinanceAssistant 💰")

# ── Simulated local expense database ────────────────────────────
# In a real project, this would be a SQLite or PostgreSQL query
EXPENSES = [
    {"date": "2026-02-01", "category": "Food",        "amount": 45000, "note": "Grocery store"},
    {"date": "2026-02-03", "category": "Transport",   "amount": 12000, "note": "Bus pass"},
    {"date": "2026-02-05", "category": "Food",        "amount": 28000, "note": "Restaurant"},
    {"date": "2026-02-10", "category": "Utilities",   "amount": 89000, "note": "Electricity bill"},
    {"date": "2026-02-12", "category": "Food",        "amount": 15000, "note": "Lunch"},
    {"date": "2026-02-14", "category": "Leisure",     "amount": 55000, "note": "Cinema + dinner"},
    {"date": "2026-02-17", "category": "Transport",   "amount": 8500,  "note": "Taxi"},
    {"date": "2026-02-18", "category": "Food",        "amount": 62000, "note": "Grocery store"},
    {"date": "2026-02-19", "category": "Leisure",     "amount": 30000, "note": "Book purchase"},
]


@mcp.tool
def get_expenses(
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    Retrieve personal expense records, optionally filtered by category or date range.
    Categories available: Food, Transport, Utilities, Leisure.
    Dates should be in YYYY-MM-DD format.
    Use this when the user asks about their spending, expenses, or transactions.
    """
    filtered = EXPENSES.copy()

    if category:
        filtered = [e for e in filtered if e["category"].lower() == category.lower()]

    if start_date:
        filtered = [e for e in filtered if e["date"] >= start_date]

    if end_date:
        filtered = [e for e in filtered if e["date"] <= end_date]

    total = sum(e["amount"] for e in filtered)

    return {
        "expenses": filtered,
        "total_KRW": total,
        "count": len(filtered),
        "currency": "KRW (Korean Won)",
    }


@mcp.tool
def summarize_by_category() -> Dict:
    """
    Summarize all expenses grouped by category with totals and percentages.
    Use this when the user asks for a spending breakdown or budget overview.
    """
    totals: Dict[str, int] = {}
    for expense in EXPENSES:
        cat = expense["category"]
        totals[cat] = totals.get(cat, 0) + expense["amount"]

    grand_total = sum(totals.values())
    summary = [
        {
            "category": cat,
            "total_KRW": amount,
            "percentage": round(amount / grand_total * 100, 1)
        }
        for cat, amount in sorted(totals.items(), key=lambda x: -x[1])
    ]

    return {
        "summary": summary,
        "grand_total_KRW": grand_total,
        "period": "February 2026",
    }


@mcp.tool
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict:
    """
    Convert an amount between currencies using live exchange rates.
    Use this when the user wants to know the value in a different currency.
    Supports major currencies: KRW, USD, EUR, JPY, GBP, etc.
    """
    try:
        # Using frankfurter.app — free, no API key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.frankfurter.app/latest",
                params={"from": from_currency.upper(), "to": to_currency.upper()}
            )
            data = response.json()

        rate = data["rates"][to_currency.upper()]
        converted = round(amount * rate, 2)

        return {
            "original_amount": amount,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "exchange_rate": rate,
            "converted_amount": converted,
        }
    except Exception as e:
        return {"error": f"Currency conversion failed: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

#### Example Queries

```python
# Query 1: Spending breakdown
"Give me a breakdown of my spending this month and tell me where I'm spending the most."

# Query 2: Category filter
"How much did I spend on food in February?"

# Query 3: Currency conversion
"How much have I spent in total this month? Convert to USD so I can understand it better."

# Query 4: Multi-tool (filter + convert)
"Show me my leisure expenses and convert the total to Japanese Yen."
```

#### Expected Multi-Tool Flow

```
🔨 Calling tool: summarize_by_category
   Result: {"summary": [{"category": "Food", "total_KRW": 150000, ...}, ...]}

🔨 Calling tool: convert_currency
   Arguments: {'amount': 344500, 'from_currency': 'KRW', 'to_currency': 'USD'}
   Result: {"converted_amount": 248.32, "exchange_rate": 0.000721}

🤖 Final Response:
Your total February spending is ₩344,500 (approximately $248.32 USD).
Your biggest expense category is Utilities at ₩89,000 (25.8%), followed by Food...
```

---

### Use Case 2: DevOps Health Monitor

**Goal:** An AI assistant that monitors system health, checks service availability, and provides actionable reports — useful for a developer or sysadmin running a homelab or small production environment.

```python
# devops_server.py
import subprocess
import platform
import psutil  # pip install psutil
import httpx
from datetime import datetime
from typing import Dict, List
from fastmcp import FastMCP

mcp = FastMCP("DevOpsMonitor 🖥️")


@mcp.tool
def get_system_health() -> Dict:
    """
    Get real-time system health metrics: CPU usage, memory, disk space, and uptime.
    Use this when the user asks about server health, system performance, or resource usage.
    Returns percentages and absolute values for all key metrics.
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time

    # Disk info for all partitions
    partitions = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partitions.append({
                "mountpoint": partition.mountpoint,
                "total_GB": round(usage.total / (1024**3), 1),
                "used_GB": round(usage.used / (1024**3), 1),
                "free_GB": round(usage.free / (1024**3), 1),
                "percent_used": usage.percent,
            })
        except PermissionError:
            continue

    return {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.system(),
        "cpu": {
            "percent_used": cpu_percent,
            "core_count": psutil.cpu_count(),
            "status": "WARNING" if cpu_percent > 80 else "OK",
        },
        "memory": {
            "total_GB": round(memory.total / (1024**3), 1),
            "available_GB": round(memory.available / (1024**3), 1),
            "percent_used": memory.percent,
            "status": "WARNING" if memory.percent > 85 else "OK",
        },
        "disk": partitions,
        "uptime_hours": round(uptime.total_seconds() / 3600, 1),
    }


@mcp.tool
async def check_service_url(url: str, timeout_seconds: int = 5) -> Dict:
    """
    Check if a web service or API endpoint is reachable and measure response time.
    Use this when the user wants to know if a service is up, down, or slow.
    Returns HTTP status code, response time, and health assessment.

    Args:
        url: Full URL to check (e.g., 'https://api.myapp.com/health')
        timeout_seconds: Maximum wait time before marking as down (default: 5)
    """
    try:
        start = datetime.now()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout_seconds)
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        return {
            "url": url,
            "status": "UP",
            "http_status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 1),
            "performance": (
                "FAST" if elapsed_ms < 200
                else "SLOW" if elapsed_ms < 1000
                else "VERY SLOW"
            ),
        }
    except httpx.TimeoutException:
        return {"url": url, "status": "DOWN", "reason": "Connection timed out"}
    except Exception as e:
        return {"url": url, "status": "DOWN", "reason": str(e)}


@mcp.tool
def get_top_processes(limit: int = 5) -> Dict:
    """
    List the top resource-consuming processes on the system.
    Use this when the user asks what is using the most CPU or memory.
    Returns process name, PID, CPU%, and memory% for the heaviest processes.
    """
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            if info["cpu_percent"] is not None:
                processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU usage
    processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)

    return {
        "top_processes": [
            {
                "pid": p["pid"],
                "name": p["name"],
                "cpu_percent": round(p["cpu_percent"], 1),
                "memory_percent": round(p.get("memory_percent", 0), 1),
            }
            for p in processes[:limit]
        ],
        "limit": limit,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

#### Example DevOps Queries

```python
# Full health check
"Run a full health check on my system and flag any warnings."

# Service monitoring
"Check if these services are up: https://google.com, https://api.myapp.com/health"

# Performance investigation
"My system feels slow. What's using the most resources right now?"

# Combined analysis
"Check system health and also check if google.com is reachable. Give me a one-paragraph summary."
```

---

### Use Case 3: Research Assistant with Web + File Tools

**Goal:** An AI assistant that can search for information, save notes to files, and load them back — a local, private research notebook.

```python
# research_server.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from fastmcp import FastMCP

mcp = FastMCP("ResearchAssistant 📚")

NOTES_DIR = Path("./research_notes")
NOTES_DIR.mkdir(exist_ok=True)


@mcp.tool
def save_note(title: str, content: str, tags: Optional[List[str]] = None) -> Dict:
    """
    Save a research note to a local file for later retrieval.
    Use this when the user wants to save, record, or remember information.
    Notes are saved with timestamps and can be tagged for organization.

    Args:
        title: Short title for the note (used as filename)
        content: The full content to save
        tags: Optional list of topic tags (e.g., ['AI', 'climate', 'research'])
    """
    note = {
        "title": title,
        "content": content,
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
    }

    # Sanitize filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    filename = NOTES_DIR / f"{safe_title}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(note, f, indent=2, ensure_ascii=False)

    return {
        "saved": True,
        "filename": str(filename),
        "title": title,
        "tags": note["tags"],
    }


@mcp.tool
def list_notes(tag: Optional[str] = None) -> Dict:
    """
    List all saved research notes, optionally filtered by tag.
    Use this when the user asks what notes they have, or wants to find notes on a topic.
    """
    notes = []
    for note_file in NOTES_DIR.glob("*.json"):
        try:
            with open(note_file, "r", encoding="utf-8") as f:
                note = json.load(f)
            if tag is None or tag.lower() in [t.lower() for t in note.get("tags", [])]:
                notes.append({
                    "title": note["title"],
                    "tags": note.get("tags", []),
                    "created_at": note.get("created_at"),
                    "filename": note_file.name,
                })
        except Exception:
            continue

    return {
        "notes": notes,
        "count": len(notes),
        "filter_tag": tag,
    }


@mcp.tool
def read_note(title: str) -> Dict:
    """
    Read the full content of a saved research note by its title.
    Use this when the user wants to recall, review, or read a specific note.
    """
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    filename = NOTES_DIR / f"{safe_title}.json"

    if not filename.exists():
        # Try partial match
        matches = list(NOTES_DIR.glob(f"*{safe_title[:10]}*.json"))
        if not matches:
            return {"error": f"Note '{title}' not found. Use list_notes to see available notes."}
        filename = matches[0]

    with open(filename, "r", encoding="utf-8") as f:
        note = json.load(f)

    return note


@mcp.tool
async def fetch_webpage_summary(url: str) -> Dict:
    """
    Fetch the content of a webpage and return its text content for analysis.
    Use this when the user wants to research a specific URL or webpage.
    Returns the raw text content (up to 5000 characters) for the LLM to summarize.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Research Bot)"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10, follow_redirects=True)

        # Very basic HTML stripping
        import re
        text = re.sub(r"<[^>]+>", " ", response.text)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url": url,
            "status_code": response.status_code,
            "content_preview": text[:5000],
            "total_chars": len(text),
        }
    except Exception as e:
        return {"error": f"Failed to fetch {url}: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

#### Example Research Queries

```python
# Save research findings
"Save a note titled 'MCP Protocol Overview' about the key points of the Model Context Protocol we discussed."

# List and recall notes
"What notes do I have tagged with 'AI'? Read the most recent one."

# Web research + save
"Fetch the content from https://modelcontextprotocol.io and save a summary as a note."
```

---

## 11. How a Real Project Is Structured

When moving beyond a single script into a maintainable project, here's how to structure it properly.

### Recommended Directory Layout

```
my-ai-agent/
│
├── README.md
├── requirements.txt
├── .env                          # API keys, secrets (never commit this)
├── .gitignore
│
├── servers/
│   ├── __init__.py
│   ├── weather_server.py         # Weather tools
│   ├── finance_server.py         # Finance tools
│   └── devops_server.py          # DevOps tools
│
├── client/
│   ├── __init__.py
│   ├── base_client.py            # Reusable client logic
│   ├── conversation.py           # Multi-turn conversation manager
│   └── formatters.py             # Output formatting helpers
│
├── config/
│   └── settings.py               # Centralized configuration
│
├── data/
│   ├── expenses.db               # SQLite for finance data
│   └── research_notes/           # Saved research files
│
├── tests/
│   ├── test_tools.py
│   └── test_client.py
│
└── scripts/
    ├── start_server.sh           # Start all MCP servers
    └── run_agent.sh              # Start the agent
```

### Configuration Management

```python
# config/settings.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()

@dataclass
class Config:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
    mcp_host: str = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("MCP_PORT", "8080"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    @property
    def mcp_url(self) -> str:
        return f"http://{self.mcp_host}:{self.mcp_port}/mcp"

config = Config()
```

### A Production-Grade Client with Multi-Turn Memory

```python
# client/conversation.py
import json
import asyncio
from typing import List, Dict, Optional
import ollama
from fastmcp import Client as MCPClient
from config.settings import config


class ConversationManager:
    """
    Manages a multi-turn conversation with tool calling support.
    Maintains full message history so the LLM has context across turns.
    """

    def __init__(self, system_prompt: Optional[str] = None):
        self.history: List[Dict] = []
        self.tools: List[Dict] = []

        if system_prompt:
            self.history.append({"role": "system", "content": system_prompt})

    async def initialize(self):
        """Load tools from MCP server."""
        async with MCPClient(config.mcp_url) as mcp:
            tools_list = await mcp.list_tools()
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    }
                }
                for t in tools_list
            ]
        print(f"✅ Loaded {len(self.tools)} tools")

    async def execute_tool(self, tool_name: str, arguments: dict):
        """Execute a tool and return its result."""
        async with MCPClient(config.mcp_url) as mcp:
            result = await mcp.call_tool(tool_name, arguments)
            return result

    async def send(self, user_message: str) -> str:
        """
        Send a message and run the full agentic loop.
        Returns the final LLM response text.
        """
        # Add user message to history
        self.history.append({"role": "user", "content": user_message})

        # Call LLM
        response = ollama.chat(
            model=config.ollama_model,
            messages=self.history,
            tools=self.tools,
            stream=False,
        )

        # Handle tool calls in a loop (LLM may want multiple rounds of tools)
        while response["message"].get("tool_calls"):
            self.history.append(response["message"])

            for tool_call in response["message"]["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
                if isinstance(args, str):
                    args = json.loads(args)

                print(f"  🔨 {tool_name}({args})")
                result = await self.execute_tool(tool_name, args)

                self.history.append({
                    "role": "tool",
                    "content": str(result),
                })

            # Let LLM respond again with new tool results
            response = ollama.chat(
                model=config.ollama_model,
                messages=self.history,
                tools=self.tools,
                stream=False,
            )

        # Add final response to history
        final_text = response["message"]["content"]
        self.history.append({"role": "assistant", "content": final_text})
        return final_text


# ── Interactive CLI ──────────────────────────────────────────────
async def interactive_session():
    """Run an interactive multi-turn chat session."""
    SYSTEM_PROMPT = """
    You are a helpful AI assistant with access to various tools.
    When using tools, always explain what you're doing and why.
    Be concise but thorough in your final responses.
    """

    agent = ConversationManager(system_prompt=SYSTEM_PROMPT)
    await agent.initialize()

    print("\n🤖 Agent ready! Type 'quit' to exit, 'clear' to reset memory.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.lower() == "quit":
            break
        elif user_input.lower() == "clear":
            await agent.initialize()
            agent.history = []
            print("🔄 Conversation cleared.\n")
            continue
        elif not user_input:
            continue

        response = await agent.send(user_input)
        print(f"\n🤖 Assistant: {response}\n")


if __name__ == "__main__":
    asyncio.run(interactive_session())
```

### Running Multiple Servers Simultaneously

In a real project, you might have separate MCP servers for different domains. Run them on different ports:

```python
# servers/weather_server.py
mcp.run(transport="http", host="127.0.0.1", port=8081, path="/mcp")

# servers/finance_server.py
mcp.run(transport="http", host="127.0.0.1", port=8082, path="/mcp")
```

Then in the client, merge tools from both:

```python
MCP_SERVERS = [
    "http://127.0.0.1:8081/mcp",  # weather
    "http://127.0.0.1:8082/mcp",  # finance
]

async def load_all_tools():
    all_tools = []
    for server_url in MCP_SERVERS:
        async with MCPClient(server_url) as mcp:
            tools = await mcp.list_tools()
            # Store which server each tool belongs to
            for t in tools:
                t._server_url = server_url  # custom attribute for routing
            all_tools.extend(tools)
    return all_tools
```

### Using a Process Manager (Production)

For running servers persistently, use `supervisor` or `systemd`:

```ini
# /etc/supervisor/conf.d/mcp-weather.conf
[program:mcp-weather]
command=/path/to/myenv/bin/python /path/to/servers/weather_server.py
autostart=true
autorestart=true
stderr_logfile=/var/log/mcp-weather.err.log
stdout_logfile=/var/log/mcp-weather.out.log
```

---

## 12. Choosing the Right Ollama Model

Model selection has a major impact on tool-calling quality. Here's what you need to know:

### Models That Support Tool Calling

| Model | Size | Tool Calling | Notes |
|-------|------|-------------|-------|
| `llama3.2` | 3B | ✅ Excellent | Best for everyday use, fast |
| `llama3.1` | 8B–70B | ✅ Excellent | Higher accuracy, more resource-heavy |
| `qwen2.5` | 7B–72B | ✅ Very good | Strong multilingual support |
| `mistral` | 7B | ✅ Good | Good for European language tasks |
| `mixtral` | 47B | ✅ Very good | Complex reasoning, resource-heavy |

### Models That Do NOT Support Tool Calling

| Model | Why | Alternative |
|-------|-----|-------------|
| `codellama` | Code-generation focus | Use `qwen2.5-coder` |
| `llama2` | Older architecture | Upgrade to `llama3.1` |
| `phi` | Simplified model | Use `llama3.2` |
| `tinyllama` | Minimal capacity | Use `llama3.2` |
| `deepseek-coder` | Code-only focus | Use `qwen2.5-coder` |

### How to Check if a Model Supports Tools

Run a simple test:

```python
import ollama

try:
    response = ollama.chat(
        model="your-model-name",
        messages=[{"role": "user", "content": "What is 5 + 3?"}],
        tools=[{
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                    "required": ["a", "b"]
                }
            }
        }],
    )
    print("✅ Tool calling supported!")
    print(response)
except Exception as e:
    if "400" in str(e):
        print("❌ This model does NOT support tool calling")
    else:
        print(f"Other error: {e}")
```

---

## 13. Debugging and Troubleshooting

### Common Errors and Fixes

**Error: "does not support tools (status code: 400)"**
```
Solution: Switch to a tool-compatible model
ollama pull llama3.2
```

**Error: "Cannot connect to FastMCP server"**
```
Check: Is mcp_server.py running?
Check: Is the URL correct? Default: http://127.0.0.1:8080/mcp
```

**Error: "Ollama connection refused"**
```
Solution: Start Ollama
ollama serve
```

**Error: "Unexpected keyword argument" in tool**
```
The LLM is passing parameters your tool doesn't expect.
Cause: Your docstring didn't clearly specify valid parameters.
Fix: Add explicit parameter documentation to your docstring.
```

**Tools are never called (LLM always answers directly)**
```
Possible causes:
1. Query is too simple — LLM knows the answer
2. Tool description doesn't match query intent
3. Model doesn't support tools

Fix: Be more explicit in the query ("Please use the add tool to compute...")
Fix: Improve the tool docstring to match natural query language
```

### Adding Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or add verbose printing in the client loop
print(f"📤 Sending to LLM with {len(tools)} tools available...")
print(f"📥 LLM response: {response['message']}")
print(f"🔧 Tool calls: {response['message'].get('tool_calls', 'None')}")
```

### Validating Tool Schemas

FastMCP auto-generates schemas, but you can inspect them:

```python
async def debug_tools():
    async with MCPClient(MCP_SERVER_URL) as mcp:
        tools = await mcp.list_tools()
        for t in tools:
            print(f"\n=== Tool: {t.name} ===")
            print(f"Description: {t.description}")
            print(f"Schema: {json.dumps(t.inputSchema, indent=2)}")
```

---

## 14. What's Next — Going Beyond

Once you have the basics down, here are the natural next steps:

### 1. Streaming Responses

```python
# Stream the final LLM response for better UX
response = ollama.chat(
    model=OLLAMA_MODEL,
    messages=messages,
    stream=True,
)

print("🤖 Assistant: ", end="", flush=True)
for chunk in response:
    print(chunk["message"]["content"], end="", flush=True)
print()
```

### 2. Persistent Conversation Memory with a Database

Replace the in-memory `history` list with a SQLite-backed conversation store:

```python
import sqlite3

def save_message(conversation_id: str, role: str, content: str):
    conn = sqlite3.connect("conversations.db")
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, datetime('now'))",
        (conversation_id, role, content)
    )
    conn.commit()
    conn.close()
```

### 3. MCP + RAG (Retrieval-Augmented Generation)

Add a tool that searches a vector database of your documents:

```python
@mcp.tool
async def search_knowledge_base(query: str, top_k: int = 3) -> Dict:
    """Search the local knowledge base for relevant information."""
    # Uses a local embedding model + vector store (e.g., chromadb)
    results = vector_db.query(query_texts=[query], n_results=top_k)
    return {"results": results["documents"][0], "distances": results["distances"][0]}
```

### 4. Web UI with Gradio or Streamlit

```python
# app.py — Gradio web interface
import gradio as gr

def respond(message, history):
    result = asyncio.run(agent.send(message))
    return result

demo = gr.ChatInterface(fn=respond, title="My AI Agent")
demo.launch()
```

### 5. Connect to Real Data Sources

```python
@mcp.tool
def query_database(sql: str) -> Dict:
    """Execute a read-only SQL query against the local database."""
    import sqlite3
    conn = sqlite3.connect("mydata.db")
    cursor = conn.execute(sql)
    return {"rows": cursor.fetchall(), "columns": [d[0] for d in cursor.description]}
```

### 6. Schedule Regular Reports

```python
# Use APScheduler to have the agent generate daily reports
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", hour=8)  # Every day at 8am
async def daily_briefing():
    response = await agent.send("Generate my daily system health and spending summary.")
    send_to_telegram(response)  # Or email, Slack, etc.
```

---

## Quick Reference Card

```
STARTUP CHECKLIST:
  □ ollama serve (or Ollama running in background)
  □ ollama pull llama3.2
  □ source myenv/bin/activate
  □ python mcp_server.py   (Terminal 1)
  □ python client_ollama.py  (Terminal 2)

GOLDEN RULES:
  1. Docstrings are your LLM's instructions — write them carefully
  2. Always handle the case where the LLM answers without tools
  3. Arguments may arrive as strings — cast defensively
  4. Error messages are read by the LLM — make them informative
  5. Async tools for any I/O (network, disk, subprocess)
  6. Test with edge cases — missing tools lead to hallucination

MODEL QUICK GUIDE:
  ✅ llama3.2       → fast, tool-capable, 3B, recommended start
  ✅ llama3.1:8b    → better reasoning, 2x slower
  ✅ qwen2.5:7b     → multilingual, very good at tools
  ❌ codellama      → NO tool support
  ❌ llama2         → NO tool support

FASTMCP QUICK SYNTAX:
  @mcp.tool          → register a tool
  @mcp.resource()    → register a data resource
  mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
```

---

*Built with FastMCP 2.14+ | Ollama | Python 3.11+*
*All examples tested and based on real outputs — including the failures that taught us the most.*