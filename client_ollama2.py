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
                ollama_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                )
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
        print(
            f"   Make sure Ollama is running and model '{OLLAMA_MODEL}' is available."
        )
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
        messages.append(
            {
                "role": "tool",
                "content": (
                    json.dumps(result) if isinstance(result, dict) else str(result)
                ),
            }
        )

    # Step 6: Final LLM call with tool results in context
    final_response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
    )

    print("🤖 Final Response:")
    print(final_response["message"]["content"])


# ── Entry Point ──────────────────────────────────────────────────
if __name__ == "__main__":
    ## Full health check
    # user_msg ="Run a full health check on my system and flag any warnings."

    ## Service monitoring
    # user_msg = "Check if these services are up: https://google.com, https://api.myapp.com/health"

    ## Performance investigation
    #user_msg ="My system feels slow. What's using the most resources right now?"

    ## Combined analysis
    # user_msg = "Check system health and also check if google.com is reachable. Give me a one-paragraph summary."
    # user_msg = "Run a full health check on my system and flag any warnings."

    ###  Research assistant
    ## Save research findings
    # user_msg = "Save a note titled 'MCP Protocol Overview' about the key points of the Model Context Protocol we discussed."

    ## List and recall notes
    # user_msg =  "What notes do I have tagged with 'AI'? Read the most recent one."

    ## Web research + save
    user_msg = "Fetch the content from https://modelcontextprotocol.io and save a summary as a note."
    asyncio.run(chat(user_msg))
