# server.py
from fastmcp import FastMCP


mcp = FastMCP("Demo 🚀")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
    #mcp.serve_http(host="127.0.0.1", port=8080)
