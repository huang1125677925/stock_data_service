"""
时间工具模块
提供获取当前时间、日期转换等接口
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime
import pytz

from mcp.server.fastmcp import FastMCP


def register_time_tools(mcp: FastMCP) -> None:
    """注册时间相关的工具"""

    @mcp.tool()
    def get_current_time(
        timezone: str = "Asia/Shanghai",
        format: str = "%Y-%m-%d %H:%M:%S",
    ) -> Dict[str, Any]:
        """
        获取当前指定时区的时间
        
        Args:
            timezone (str): 时区，默认 "Asia/Shanghai"
            format (str): 时间格式，默认 "%Y-%m-%d %H:%M:%S"
            
        Returns:
            Dict[str, Any]: 包含当前时间的字典
        """
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            return {
                "code": 200,
                "message": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "current_time": current_time.strftime(format),
                    "timezone": timezone,
                    "timestamp": int(current_time.timestamp())
                }
            }
        except Exception as e:
            from mcp_service.tools.tushare._registry import error_payload
            return error_payload(f"Failed to get current time: {str(e)}", 500)

    @mcp.tool()
    def get_current_date(
        timezone: str = "Asia/Shanghai",
        format: str = "%Y%m%d",
    ) -> Dict[str, Any]:
        """
        获取当前指定时区的日期（常用于股票数据接口的 trade_date 等参数）
        
        Args:
            timezone (str): 时区，默认 "Asia/Shanghai"
            format (str): 日期格式，默认 "%Y%m%d"
            
        Returns:
            Dict[str, Any]: 包含当前日期的字典
        """
        try:
            tz = pytz.timezone(timezone)
            current_date = datetime.now(tz)
            return {
                "code": 200,
                "message": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "current_date": current_date.strftime(format),
                    "timezone": timezone
                }
            }
        except Exception as e:
            from mcp_service.tools.tushare._registry import error_payload
            return error_payload(f"Failed to get current date: {str(e)}", 500)
