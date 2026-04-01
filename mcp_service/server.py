import sys
import os
from pathlib import Path

# Resolve project root from this file's location
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "tushare_docs"

# Add project root to Python path to enable imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from mcp_service.tavily_mcp_service import register_tavily_mcp_client


def create_server() -> FastMCP:
    """
    Create and configure the FastMCP server instance.
    Registers modular tools for Tushare docs and interfaces.
    """
    # Rename MCP as requested
    mcp = FastMCP(name="tushareMCP")

    # Register modular tools
    from mcp_service.tools.news_data_tools import register_news_data_tools
    from mcp_service.tools.jin10_flash_tools import register_jin10_flash_tools
    from mcp_service.tools.stock_data_tools import register_stock_data_tools
    from mcp_service.tools.tushare import register_tushare_tools
    from mcp_service.tools.time_tools import register_time_tools
    from mcp_service.tools.django_strategy_tools import register_django_strategy_tools

    register_news_data_tools(mcp)
    register_jin10_flash_tools(mcp)
    register_stock_data_tools(mcp)
    register_tushare_tools(mcp)
    register_django_strategy_tools(mcp)
    register_time_tools(mcp)
    register_tavily_mcp_client(
        url=os.getenv("TAVILY_MCP_URL", ""),
        enabled=os.getenv("TAVILY_MCP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
        timeout_seconds=int(os.getenv("TAVILY_MCP_TIMEOUT_SECONDS", "30")),
    )
    return mcp


# Create server for CLI discovery (fastmcp/mcp tools look for mcp/app/server)
mcp = create_server()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the FastMCP server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8008, help="Server port")
    parser.add_argument("--path", type=str, default="/tushare/mcp", help="Path prefix for SSE (mount path)")
    args = parser.parse_args()
    
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    
    # FastMCP uses sse_path and message_path for its internal Starlette routes.
    # To properly prefix the URLs when running directly via Uvicorn, 
    # we need to prepend the path to these route settings.
    if args.path:
        base_path = args.path.rstrip("/")
        mcp.settings.sse_path = f"{base_path}/sse"
        mcp.settings.message_path = f"{base_path}/messages/"
    
    # Run with SSE transport so clients can connect via SSE
    # Default host: 0.0.0.0, port: 8000 (can be overridden via CLI)
    mcp.run(transport="sse")
