from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare.stock_data.basic_data import register_stock_basic_tools
from mcp_service.tools.tushare.stock_data.finance_data import (
    register_stock_finance_tools,
)
from mcp_service.tools.tushare.stock_data.margin_data import register_stock_margin_tools
from mcp_service.tools.tushare.stock_data.market_data import register_stock_market_tools
from mcp_service.tools.tushare.stock_data.moneyflow_data import (
    register_stock_moneyflow_tools,
)
from mcp_service.tools.tushare.stock_data.reference_data import (
    register_stock_reference_data_tools,
)
from mcp_service.tools.tushare.stock_data.special_data import (
    register_stock_special_tools,
)
from mcp_service.tools.tushare.stock_data.topic_data import register_stock_topic_tools


def register_stock_data_tools(mcp: FastMCP) -> None:
    register_stock_basic_tools(mcp)
    register_stock_market_tools(mcp)
    register_stock_finance_tools(mcp)
    register_stock_reference_data_tools(mcp)
    register_stock_moneyflow_tools(mcp)
    register_stock_margin_tools(mcp)
    register_stock_special_tools(mcp)
    register_stock_topic_tools(mcp)
