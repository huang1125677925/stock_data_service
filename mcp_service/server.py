import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Resolve project root from this file's location
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "tushare_docs"

# Add project root to Python path to enable imports
sys.path.insert(0, str(PROJECT_ROOT))


def create_server() -> FastMCP:
    """
    Create and configure the FastMCP server instance.
    Registers modular tools for Tushare docs and interfaces.
    """
    # Rename MCP as requested
    mcp = FastMCP(name="tushareMCP")

    # Register modular tools
    from mcp_service.tools.news_data_tools import register_news_data_tools
    from mcp_service.tools.stock_data_tools import register_stock_data_tools

    register_news_data_tools(mcp)
    register_stock_data_tools(mcp)
    return mcp


# Create server for CLI discovery (fastmcp/mcp tools look for mcp/app/server)
mcp = create_server()


if __name__ == "__main__":
    # Run with SSE transport so clients can connect via SSE
    # Default host: 0.0.0.0, port: 8000 (can be overridden via env/CLI)
    mcp.run(transport="sse")