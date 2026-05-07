"""
新闻数据工具模块

提供新闻快讯、上市公司公告、新闻联播、新闻通讯、上证E互动等数据接口工具。
所有接口都通过 scheduled_tasks 中的 Tushare 代理来获取数据，遵循架构规范。

分页约定（不截断正文）：单次只返回一页 records；需要全量时保持其它查询参数不变，
根据返回的 has_more / next_offset / remaining 递增 offset 再次调用，直至 has_more 为 false。
缩小单次体量还可传 fields（逗号分隔，与 Tushare 文档一致）只取需要的列。
"""

from __future__ import annotations
from typing import Dict, Optional
from mcp.server.fastmcp import FastMCP
from common.response import error_response
from mcp_service.tools.tushare._registry import apply_pagination


def register_news_data_tools(mcp: FastMCP) -> None:
    """
    注册新闻数据相关的工具函数

    包含以下接口：
    1. news - 新闻快讯
    2. anns_d - 上市公司公告
    3. cctv_news - 新闻联播文字稿
    4. major_news - 新闻通讯
    5. irm_qa_sh - 上证E互动问答
    """

    def _call_tushare_proxy(
        interface: str,
        params: Optional[Dict] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """调用通用 Tushare 代理（common模块），集中外部访问逻辑"""
        try:
            from common.tushare_proxy import call_tushare

            return call_tushare(
                interface=interface,
                params=params or {},
                token=token,
                fields=fields,
                use_query=False,
            )
        except Exception as e:
            return error_response(f"调用 Tushare 代理失败: {str(e)}")

    @mcp.tool()
    def get_news_flash(
        src: str,
        start_date: str,
        end_date: str,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """
        获取新闻快讯数据

        接口：news
        描述：获取主流新闻网站的快讯新闻数据，提供超过6年以上历史新闻
        限量：单次最大1500条新闻，可根据时间参数循环提取历史

        参数说明：
        - src (str, 必选): 新闻来源，支持：sina / wallstreetcn / 10jqka / eastmoney /
          yuncaijing / fenghuang / jinrongjie / cls / yicai
        - start_date (str, 必选): 开始日期，格式：'2018-11-20 09:00:00'
        - end_date (str, 必选): 结束日期，格式：'2018-11-20 22:05:03'
        - limit (int): 本页条数上限，默认20，最大500（仅控制本次返回，不截断字段内容）
        - offset (int): 本页起始偏移，默认0；若 data.has_more 为 true，用 data.next_offset 继续请求
        - fields (str, 可选): 逗号分隔字段名，不传则由上游返回默认列；可只取 datetime,title 等以减小体积
        - token (str, 可选): Tushare API token

        返回 data 元信息：total_count / count / limit / offset / has_more / next_offset / remaining
        """
        params = {"src": src, "start_date": start_date, "end_date": end_date}
        safe_limit = max(1, min(int(limit or 20), 500))
        safe_offset = max(0, int(offset or 0))
        resp = _call_tushare_proxy("news", params, fields=fields, token=token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @mcp.tool()
    def get_company_announcements(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """
        获取上市公司全量公告数据

        接口：anns_d
        限量：单次最大2000条，可用 limit/offset 分页拉全量。

        - limit (int): 本页条数，默认50，最大500
        - offset (int): 偏移；下一页用返回的 next_offset
        - fields (str, 可选): 逗号分隔字段，缩小列集合
        """
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        safe_limit = max(1, min(int(limit or 50), 500))
        safe_offset = max(0, int(offset or 0))
        resp = _call_tushare_proxy("anns_d", params, fields=fields, token=token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @mcp.tool()
    def get_cctv_news(
        date: str,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """
        获取新闻联播文字稿数据

        接口：cctv_news
        - date (str, 必选): 日期，格式：'20181211' (YYYYMMDD)
        - limit (int): 本页条数（按段），默认20，最大200
        - offset (int): 分页偏移；同一天条数多时分页取全量
        - fields (str, 可选): 逗号分隔字段
        """
        params = {"date": date}
        safe_limit = max(1, min(int(limit or 20), 200))
        safe_offset = max(0, int(offset or 0))
        resp = _call_tushare_proxy("cctv_news", params, fields=fields, token=token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @mcp.tool()
    def get_major_news(
        src: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_content: bool = False,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """
        获取新闻通讯（长篇）数据

        接口：major_news
        - include_content (bool): 是否包含正文列；False 时仅标题等，单次 token 更小
        - limit (int): 本页条数，默认10，最大200
        - offset (int): 分页偏移
        - fields (str, 可选): 若指定则覆盖默认列选择（与 include_content 同时用时以显式 fields 为准）
        """
        params = {}
        if src:
            params["src"] = src
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        effective_fields = fields
        if effective_fields is None and include_content:
            effective_fields = "title,content,pub_time,src"
        elif effective_fields is None and not include_content:
            effective_fields = "title,pub_time,src"

        safe_limit = max(1, min(int(limit or 10), 200))
        safe_offset = max(0, int(offset or 0))
        resp = _call_tushare_proxy("major_news", params, fields=effective_fields, token=token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @mcp.tool()
    def get_shanghai_interactive_qa(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        pub_date_start: Optional[str] = None,
        pub_date_end: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """
        获取上证E互动问答数据（irm_qa_sh）

        - limit / offset: 分页；全量则循环至 has_more 为 false
        - fields (str, 可选): 只取必要列时可不传 q/a，例如 ts_code,trade_date,pub_time
        """
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if pub_date_start:
            params["pub_date"] = pub_date_start
        if pub_date_end:
            params["pub_date"] = pub_date_end

        safe_limit = max(1, min(int(limit or 20), 500))
        safe_offset = max(0, int(offset or 0))
        resp = _call_tushare_proxy("irm_qa_sh", params, fields=fields, token=token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @mcp.tool()
    def get_shenzhen_interactive_qa(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        pub_date_start: Optional[str] = None,
        pub_date_end: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict:
        """
        获取深证互动易问答数据（irm_qa_sz）

        - limit / offset: 分页取全量
        - fields (str, 可选): 按需缩小列集合
        """
        params = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if pub_date_start:
            params["pub_date"] = pub_date_start
        if pub_date_end:
            params["pub_date"] = pub_date_end

        safe_limit = max(1, min(int(limit or 20), 500))
        safe_offset = max(0, int(offset or 0))
        resp = _call_tushare_proxy("irm_qa_sz", params, fields=fields, token=token)
        return apply_pagination(resp, safe_limit, safe_offset)
