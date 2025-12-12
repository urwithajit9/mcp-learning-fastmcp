# ollama_client.py
import json
import ollama
from fastmcp import Client as MCPClient
import asyncio
import sys

OLLAMA_MODEL = "llama3.2:latest"
MCP_SERVER_URL = "http://127.0.0.1:8080/mcp"


# ------------------------------------------------------------
# Load MCP tools using FastMCP Client
# ------------------------------------------------------------
async def load_mcp_tools():
    try:
        async with MCPClient(MCP_SERVER_URL) as mcp:
            # List available tools from the MCP server
            tools_list = await mcp.list_tools()

            # Convert to Ollama tool format
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
        print(f"ERROR connecting to FastMCP server: {e}")
        print(f"\nMake sure the FastMCP server is running at {MCP_SERVER_URL}")
        print("  python mcp_server.py")
        sys.exit(1)


# ------------------------------------------------------------
# Execute tool using FastMCP client
# ------------------------------------------------------------
async def execute_tool(tool_name: str, arguments: dict):
    try:
        async with MCPClient(MCP_SERVER_URL) as mcp:
            result = await mcp.call_tool(tool_name, arguments)
            return result
    except Exception as e:
        print(f"ERROR executing tool {tool_name}: {e}")
        return {"error": str(e)}


# ------------------------------------------------------------
# LLM + Tools Loop
# ------------------------------------------------------------
async def main():
    print("Loading MCP tools...")
    tools = await load_mcp_tools()
    print(f"Loaded {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    print()

    user_msg = "Please greet John and then add 150 + 75."
    print(f"User: {user_msg}\n")

    # First call to model
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": user_msg}],
            tools=tools,
            stream=False,
        )
    except Exception as e:
        print(f"ERROR calling Ollama: {e}")
        print(f"\nMake sure Ollama is running and model '{OLLAMA_MODEL}' is installed:")
        print(f"  ollama pull {OLLAMA_MODEL}")
        sys.exit(1)

    # Check for tool call
    if not response.get("message", {}).get("tool_calls"):
        print("LLM answered directly:")
        print(response["message"]["content"])
        return

    # Process all tool calls
    messages = [{"role": "user", "content": user_msg}, response["message"]]

    for tool_call in response["message"]["tool_calls"]:
        tool_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]

        # Parse arguments if they're a string
        if isinstance(args, str):
            args = json.loads(args)

        print(f"Tool requested: {tool_name}")
        print(f"Arguments: {args}")

        # Execute tool
        tool_result = await execute_tool(tool_name, args)
        print(f"Tool result: {tool_result}\n")

        # Add tool response to messages
        messages.append(
            {
                "role": "tool",
                "content": (
                    json.dumps(tool_result)
                    if isinstance(tool_result, dict)
                    else str(tool_result)
                ),
            }
        )

    # Feed results back to model for final response
    final = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
    )

    print("Final LLM response:")
    print(final["message"]["content"])


if __name__ == "__main__":
    asyncio.run(main())
