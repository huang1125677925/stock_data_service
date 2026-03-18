from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare.bonds import register_bonds_tools
from mcp_service.tools.tushare.etf import register_etf_tools
from mcp_service.tools.tushare.forex import register_forex_tools
from mcp_service.tools.tushare.futures import register_futures_tools
from mcp_service.tools.tushare.hk_stock import register_hk_stock_tools
from mcp_service.tools.tushare.index import register_index_tools
from mcp_service.tools.tushare.macro import register_macro_tools
from mcp_service.tools.tushare.options import register_options_tools
from mcp_service.tools.tushare.public_fund import register_public_fund_tools
from mcp_service.tools.tushare.stock_data import register_stock_data_tools
from mcp_service.tools.tushare.us_stock import register_us_stock_tools


def register_tushare_tools(mcp: FastMCP) -> None:
    register_bonds_tools(mcp)
    register_stock_data_tools(mcp)
    register_etf_tools(mcp)
    register_index_tools(mcp)
    register_hk_stock_tools(mcp)
    register_public_fund_tools(mcp)
    register_us_stock_tools(mcp)
    register_forex_tools(mcp)
    register_options_tools(mcp)
    register_futures_tools(mcp)
    register_macro_tools(mcp)
