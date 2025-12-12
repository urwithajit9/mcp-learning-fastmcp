# MCP + Ollama Agentic AI

A complete implementation of Model Context Protocol (MCP) with Ollama, enabling local LLMs to call tools and functions using FastMCP.

## 🎯 What This Does

This project demonstrates how to build an agentic AI system where:
- **Ollama** (local LLM) generates responses and decides when to use tools
- **FastMCP** provides a standardized protocol for tool communication
- **Python client** orchestrates the conversation flow between LLM and tools

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │  Query  │                  │  Tool   │                 │
│  Ollama LLM     │◄───────►│  Python Client   │◄───────►│  FastMCP Server │
│  (llama3.2)     │         │  (Orchestrator)  │         │  (Tools)        │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

### Flow:
1. **User sends query** → Client
2. **Client forwards** → Ollama LLM with available tools
3. **LLM decides** if it needs to call a tool
4. **If tool needed** → Client calls tool via FastMCP
5. **Tool result** → Back to LLM for final answer
6. **Final response** → User

## 📋 Prerequisites

- **Python 3.11+**
- **Ollama** installed and running
- **Virtual environment** (recommended)

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install packages
pip install fastmcp ollama requests
```

### Step 2: Install and Start Ollama

```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.ai/download

# Pull a model that supports tool calling
ollama pull llama3.2
```

### Step 3: Start the FastMCP Server

Open **Terminal 1**:

```bash
python mcp_server.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8080
```

### Step 4: Run the Client

Open **Terminal 2**:

```bash
python client_ollama.py
```

## 📝 Example Output

```
Loading MCP tools...
Loaded 2 tools:
  - add: Add two numbers
  - greet: None

User: Please greet John and then add 150 + 75.

Tool requested: greet
Arguments: {'name': 'John'}
Tool result: Hello, John! Welcome!

Tool requested: add
Arguments: {'a': 150, 'b': 75}
Tool result: 225

Final LLM response:
Hello John! Welcome! The sum of 150 and 75 is 225.
```

## 🛠️ Available Tools

The MCP server (`mcp_server.py`) provides these tools:

| Tool | Description | Parameters |
|------|-------------|------------|
| `add` | Add two numbers | `a: int, b: int` |
| `greet` | Greet someone | `name: str` |
| `multiply` | Multiply two numbers | `a: float, b: float` |

### Adding Custom Tools

Edit `mcp_server.py`:

```python
@mcp.tool()
def your_custom_tool(param1: str, param2: int) -> str:
    """Description of what your tool does"""
    # Your logic here
    return f"Result: {param1} - {param2}"
```

Restart the server, and the tool will automatically be available!

## 🤖 Ollama Models: Tool Calling Support

### ✅ Models That Support Tool Calling

These models can understand function schemas and decide when to call tools:

| Model | Size | Best For | Command |
|-------|------|----------|---------|
| **llama3.2** | 3B | General use, fast | `ollama pull llama3.2` |
| **llama3.1** | 8B-70B | High accuracy | `ollama pull llama3.1` |
| **mistral** | 7B | European languages | `ollama pull mistral` |
| **mixtral** | 8x7B | Complex reasoning | `ollama pull mixtral` |
| **qwen2.5** | 7B-72B | Multilingual | `ollama pull qwen2.5` |
| **command-r** | 35B | Enterprise tasks | `ollama pull command-r` |
| **command-r-plus** | 104B | Advanced reasoning | `ollama pull command-r-plus` |

### ❌ Models That DON'T Support Tool Calling

These models will return a 400 error when trying to use tools:

| Model | Why No Tools | Alternative |
|-------|--------------|-------------|
| **codellama** | Code generation only | Use llama3.2 |
| **llama2** | Older architecture | Upgrade to llama3.1 |
| **deepseek-coder** | Code-focused | Use qwen2.5-coder |
| **phi** | Small, simple tasks | Use llama3.2 |
| **tinyllama** | Minimal model | Use llama3.2 |

### Changing the Model

Edit `client_ollama.py`:

```python
OLLAMA_MODEL = "llama3.1"  # Change to any tool-compatible model
```

## 🔧 How It Works

### 1. Tool Discovery

```python
async def load_mcp_tools():
    async with MCPClient(MCP_SERVER_URL) as mcp:
        tools_list = await mcp.list_tools()
        # Convert to Ollama format
        return ollama_tools
```

The client connects to FastMCP and retrieves available tools dynamically.

### 2. LLM Decision Making

```python
response = ollama.chat(
    model=OLLAMA_MODEL,
    messages=[{"role": "user", "content": user_msg}],
    tools=tools,  # LLM sees available tools
    stream=False,
)
```

Ollama receives the tool schemas and decides whether to:
- Answer directly
- Call one or more tools

### 3. Tool Execution

```python
async def execute_tool(tool_name: str, arguments: dict):
    async with MCPClient(MCP_SERVER_URL) as mcp:
        result = await mcp.call_tool(tool_name, arguments)
        return result
```

The client executes the requested tool via FastMCP.

### 4. Final Response

```python
final = ollama.chat(
    model=OLLAMA_MODEL,
    messages=messages,  # Includes tool results
)
```

Tool results are fed back to the LLM for a natural language response.

## 🐛 Troubleshooting

### Error: "does not support tools (status code: 400)"

**Solution:** Use a tool-compatible model like `llama3.2`

```bash
ollama pull llama3.2
```

Then update `OLLAMA_MODEL = "llama3.2"` in `client_ollama.py`

### Error: "Cannot connect to FastMCP server"

**Solution:** Make sure the MCP server is running:

```bash
python mcp_server.py
```

### Error: "Ollama connection refused"

**Solution:** Start Ollama service:

```bash
ollama serve
```

### Tools not being called

**Possible causes:**
1. Model doesn't support tools → Switch to llama3.2
2. Prompt too vague → Be more specific about what you want
3. Tool description unclear → Improve tool docstrings

## 📂 Project Structure

```
mcp-fastmcp-agenticAI/
├── mcp_server.py          # FastMCP server with tools
├── client_ollama.py       # Ollama client orchestrator
├── README.md              # This file
└── myenv/                 # Virtual environment (gitignored)
```

## 🎓 Learn More

- **FastMCP Documentation:** https://gofastmcp.com
- **Ollama Documentation:** https://ollama.ai/docs
- **MCP Protocol:** https://modelcontextprotocol.io

## 📄 License

MIT License - feel free to use this in your projects!

<!-- ## 🤝 Contributing

Contributions welcome! Ideas:
- Add more example tools
- Support for streaming responses
- Multi-turn conversations with memory
- Integration with other LLM providers -->

---

**Built with:** FastMCP 2.14.0 | Ollama | Python 3.11+