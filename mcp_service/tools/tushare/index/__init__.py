from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from index_data.sw_valuation_analysis import run_sw_valuation_analysis
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool
from mcp_service.tools.tushare.index.index_sentiment import (
    compute_sentiment_from_series,
    default_lookback_dates,
    prepare_daily_rows,
)


def register_index_tools(mcp: FastMCP) -> None:
    def _call(
        interface: str,
        params: Dict[str, Any],
        fields: Optional[str],
        token: Optional[str],
    ) -> Dict[str, Any]:
        return call_tushare(
            interface=interface,
            params=params,
            fields=fields,
            token=token,
            use_query=False,
        )

    def _paginate(resp: Dict[str, Any], limit: int, offset: int, max_limit: int = 500) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), max_limit))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    def _merge_index_basic_records(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多次 index_basic 调用的 records，按 ts_code 去重；遇非 200 则返回首个错误响应。"""
        merged: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for resp in responses:
            if resp.get("code") != 200:
                return resp
            for rec in (resp.get("data") or {}).get("records") or []:
                code = rec.get("ts_code")
                key = str(code) if code is not None else ""
                if key and key not in seen:
                    seen.add(key)
                    merged.append(rec)
        return {
            "code": 200,
            "message": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "interface": "index_basic",
                "count": len(merged),
                "records": merged,
            },
        }

    @safe_tool(
        mcp,
        name="tushare.index.index_basic",
        description=(
            "指数元数据目录 index_basic（名称/发布方/基期等）。"
            "含 market=SW 的申万指数条目，但不含行业涨跌幅/估值/成分股明细；"
            "分析申万行业表现请用 sw_daily / rt_sw_k / django.index.sw_valuation_analysis。"
        ),
    )
    def index_basic(
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        market: Optional[str] = None,
        publisher: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数元数据 index_basic（非行情）。申万行业涨跌与 PE/PB 等请用 sw_daily，勿仅用本接口做行业分析。"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if name:
            params["name"] = name
        if market:
            params["market"] = market
        if publisher:
            params["publisher"] = publisher
        if category:
            params["category"] = category
        return _paginate(_call("index_basic", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_basic_search",
        description=(
            "指数元数据检索：在 index_basic 之上提供「简称/全称子串」本地模糊筛选（name_contains），"
            "以及 ts_codes 逗号分隔批量按代码查询（合并去重）。"
            "须至少提供 name_contains 或 ts_code/ts_codes 之一；"
            "精确简称查询仍用 tushare.index.index_basic。"
        ),
    )
    def index_basic_search(
        ts_code: Optional[str] = None,
        ts_codes: Optional[str] = None,
        name: Optional[str] = None,
        name_contains: Optional[str] = None,
        market: Optional[str] = None,
        publisher: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数元数据：名称子串筛选与多代码批量查询。底层仍调用 index_basic。"""
        max_batch_codes = 50
        code_list: List[str] = []
        if ts_code and str(ts_code).strip():
            code_list.append(str(ts_code).strip())
        if ts_codes:
            for part in str(ts_codes).split(","):
                c = part.strip()
                if c and c not in code_list:
                    code_list.append(c)
        if len(code_list) > max_batch_codes:
            return error_payload(
                f"ts_code/ts_codes 合计最多 {max_batch_codes} 个",
                400,
                interface="index_basic_search",
            )

        needle = (name_contains or "").strip()
        if not needle and not code_list:
            return error_payload(
                "请至少提供 name_contains，或 ts_code/ts_codes 之一",
                400,
                interface="index_basic_search",
            )

        base_params: Dict[str, Any] = {}
        if name:
            base_params["name"] = name
        if market:
            base_params["market"] = market
        if publisher:
            base_params["publisher"] = publisher
        if category:
            base_params["category"] = category

        if len(code_list) > 1:
            responses = [
                _call("index_basic", {**base_params, "ts_code": c}, fields, token)
                for c in code_list
            ]
            resp = _merge_index_basic_records(responses)
        elif len(code_list) == 1:
            params = {**base_params, "ts_code": code_list[0]}
            resp = _call("index_basic", params, fields, token)
        else:
            params = dict(base_params)
            resp = _call("index_basic", params, fields, token)

        if resp.get("code") != 200:
            return resp

        if needle:
            data = resp.get("data") or {}
            recs = data.get("records") or []
            nlow = needle.casefold()
            filtered = [
                r
                for r in recs
                if nlow in str(r.get("name") or "").casefold()
                or nlow in str(r.get("fullname") or "").casefold()
            ]
            data["count"] = len(filtered)
            data["records"] = filtered
            resp["data"] = data

        return _paginate(resp, limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_daily",
        description=(
            "通用指数日线 index_daily（沪深300、上证50 等）。"
            "Tushare 规则：本接口不含申万行业指数日线；"
            "申万行业代码如 801010.SI 的行情必须用 sw_daily，勿用 index_daily。"
        ),
    )
    def index_daily(
        ts_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """通用指数日线 index_daily。申万行业指数请改用 sw_daily（index_daily 无申万行业数据）。"""
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="index_daily")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_daily", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_sentiment",
        description=(
            "指数情绪综合分：基于 index_basic 校验元信息、index_daily 计算动量/均线/当日强弱，"
            "输出 0–100 分与交易参考提示（非投资建议）"
        ),
    )
    def index_sentiment(
        ts_code: str,
        as_of_trade_date: Optional[str] = None,
        lookback_calendar_days: int = 300,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询指定指数的情绪数值，供是否交易参考。数据源自 Tushare index_basic、index_daily。

        Args:
            ts_code: 指数代码，如 000300.SH
            as_of_trade_date: 可选，只使用该日及之前的日线（YYYYMMDD），用于复盘/回测视角
            lookback_calendar_days: 向前取日线窗口的自然日长度，默认约 300 天以保证足够交易日
            token: Tushare token
        """
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="index_sentiment")
        try:
            lb = max(120, min(int(lookback_calendar_days or 300), 800))
        except (TypeError, ValueError):
            lb = 300
        basic = _call(
            "index_basic",
            {"ts_code": ts_code},
            "ts_code,name,market,category,fullname",
            token,
        )
        if basic.get("code") != 200:
            return basic
        basic_recs = (basic.get("data") or {}).get("records") or []
        if not basic_recs:
            return error_payload(
                f"未查到指数基础信息：{ts_code}（请确认代码与 index_basic 一致）",
                404,
                interface="index_sentiment",
            )
        meta = basic_recs[0]
        start_d, end_d = default_lookback_dates(lb)
        daily = _call(
            "index_daily",
            {"ts_code": ts_code, "start_date": start_d, "end_date": end_d},
            "ts_code,trade_date,open,high,low,close,pre_close,pct_chg,vol,amount",
            token,
        )
        if daily.get("code") != 200:
            return daily
        records = (daily.get("data") or {}).get("records") or []
        rows = prepare_daily_rows(records, as_of_trade_date=as_of_trade_date)
        payload, err = compute_sentiment_from_series(rows, index_meta=meta)
        if err:
            return error_payload(err, 422, interface="index_sentiment")
        return {
            "code": 200,
            "message": "success",
            "timestamp": datetime.now().isoformat(),
            "data": payload,
        }

    @safe_tool(
        mcp,
        name="tushare.index.index_weekly",
        description="指数周线行情 index_weekly",
    )
    def index_weekly(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 26,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数周线行情 index_weekly。limit默认26（半年），最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_weekly", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_monthly",
        description="指数月线行情 index_monthly",
    )
    def index_monthly(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 24,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数月线行情 index_monthly。limit默认24（2年），最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_monthly", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_weight",
        description="指数成分和权重 index_weight",
    )
    def index_weight(
        index_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数成分和权重 index_weight。limit默认100，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not index_code:
            return error_payload(
                "index_code 为必填参数",
                400,
                interface="index_weight",
            )
        params: Dict[str, Any] = {"index_code": index_code}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_weight", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_dailybasic",
        description="大盘指数每日指标 index_dailybasic",
    )
    def index_dailybasic(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """大盘指数每日指标 index_dailybasic。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not (trade_date or ts_code or start_date or end_date):
            return error_payload(
                "trade_date 或 ts_code 或 start_date/end_date 至少提供一个参数",
                400,
                interface="index_dailybasic",
            )
        return _paginate(_call("index_dailybasic", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_global",
        description="国际主要指数日线行情 index_global",
    )
    def index_global(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """国际主要指数日线行情 index_global。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_global", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.idx_factor_pro",
        description=(
            "指数技术因子 idx_factor_pro（覆盖大盘/申万/中信等 ts_code）。"
            "若用户要「申万行业」涨跌与估值截面，优先 sw_daily 或 django.index.sw_valuation_analysis；"
            "本接口侧重技术面因子序列。"
        ),
    )
    def idx_factor_pro(
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """技术面因子序列。行业轮动/行业涨跌幅排名优先配合 sw_daily。"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if trade_date:
            params["trade_date"] = trade_date
        return _paginate(_call("idx_factor_pro", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.daily_info",
        description="市场交易统计 daily_info",
    )
    def daily_info(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """市场交易统计 daily_info。limit默认30，最大500；offset翻页。"""
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if exchange:
            params["exchange"] = exchange
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("daily_info", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.sz_daily_info",
        description="深圳市场每日交易概况 sz_daily_info",
    )
    def sz_daily_info(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """深圳市场每日交易概况 sz_daily_info。limit默认30，最大500；offset翻页。"""
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("sz_daily_info", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_classify",
        description=(
            "仅返回申万行业「分类树/代码表」index_classify（层级与行业代码，无收盘价/成交量/PE）。"
            "用户问申万行业数据、行业表现、涨跌、估值、分析时勿单独选本工具，应配合或改用 sw_daily；"
            "src 须为 SW2014 或 SW2021（勿传 SW）。"
        ),
    )
    def index_classify(
        index_code: Optional[str] = None,
        level: Optional[str] = None,
        parent_code: Optional[str] = None,
        src: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """行业分类目录 only。分析行情用 sw_daily；src 用 SW2021/SW2014。"""
        params: Dict[str, Any] = {}
        if index_code:
            params["index_code"] = index_code
        if level:
            params["level"] = level
        if parent_code:
            params["parent_code"] = parent_code
        if src:
            params["src"] = src
        return _paginate(_call("index_classify", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_member_all",
        description=(
            "申万行业成分股 index_member_all（某级行业下有哪些股票，或某股所属行业）。"
            "不含行业指数涨跌；行业指数行情用 sw_daily。"
        ),
    )
    def index_member_all(
        l1_code: Optional[str] = None,
        l2_code: Optional[str] = None,
        l3_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        is_new: str = "Y",
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """申万分级成分股。与 sw_daily（行业指数行情）分工：成分用本接口，涨跌/量能用 sw_daily。"""
        params: Dict[str, Any] = {}
        if l1_code:
            params["l1_code"] = l1_code
        if l2_code:
            params["l2_code"] = l2_code
        if l3_code:
            params["l3_code"] = l3_code
        if ts_code:
            params["ts_code"] = ts_code
        if is_new:
            params["is_new"] = is_new
        return _paginate(_call("index_member_all", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.sw_daily",
        description=(
            "申万行业指数日线 sw_daily（行业涨跌幅、开高低收、成交量、PE/PB 等）——"
            "用户问「申万行业数据/行业表现/行业分析」时的首选行情接口；"
            "与 index_classify（仅目录）不同，与 index_daily（不含申万行业）不同。"
        ),
    )
    def sw_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """申万行业指数日线（默认 2021 版行情）。可按 trade_date 拉当日全行业截面，或 ts_code+区间拉单行业走势。"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("sw_daily", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.ci_index_member",
        description="中信行业成分 ci_index_member",
    )
    def ci_index_member(
        l1_code: Optional[str] = None,
        l2_code: Optional[str] = None,
        l3_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        is_new: str = "Y",
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """中信行业成分 ci_index_member。limit默认100，最大500；offset翻页。"""
        params: Dict[str, Any] = {}
        if l1_code:
            params["l1_code"] = l1_code
        if l2_code:
            params["l2_code"] = l2_code
        if l3_code:
            params["l3_code"] = l3_code
        if ts_code:
            params["ts_code"] = ts_code
        if is_new:
            params["is_new"] = is_new
        return _paginate(_call("ci_index_member", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.ci_daily",
        description="中信行业指数日线行情 ci_daily",
    )
    def ci_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """中信行业指数日线行情 ci_daily。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("ci_daily", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.idx_mins",
        description="指数历史分钟 idx_mins",
    )
    def idx_mins(
        ts_code: str,
        freq: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 120,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="idx_mins")
        if not freq:
            return error_payload("freq 为必填参数", 400, interface="idx_mins")
        params: Dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("idx_mins", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.rt_idx_k",
        description="交易所指数实时日线 rt_idx_k",
    )
    def rt_idx_k(
        ts_code: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="rt_idx_k")
        return _call("rt_idx_k", {"ts_code": ts_code}, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.rt_idx_min",
        description="交易所指数实时分钟 rt_idx_min（freq 为大写 1MIN 等）",
    )
    def rt_idx_min(
        ts_code: str,
        freq: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="rt_idx_min")
        if not freq:
            return error_payload("freq 为必填参数（如 1MIN、5MIN）", 400, interface="rt_idx_min")
        return _call("rt_idx_min", {"ts_code": ts_code, "freq": freq}, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.rt_sw_k",
        description=(
            "申万行业指数最新截面/实时行情 rt_sw_k（当前或最新报价类数据）。"
            "历史日线序列与估值分析仍用 sw_daily 或 django.index.sw_valuation_analysis。"
        ),
    )
    def rt_sw_k(
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        return _call("rt_sw_k", params, fields, token)

    @safe_tool(
        mcp,
        name="django.index.sw_valuation_analysis",
        description=(
            "申万行业估值分析 sw_valuation_analysis（区间内 PE/PB 及历史分位数，适合「行业贵不贵/估值分位」类问题）。"
            "需要原始逐日 K 线时用 sw_daily；仅需行业代码表时用 index_classify。"
        ),
    )
    def sw_valuation_analysis(
        start_date: str,
        end_date: str,
        level: Optional[str] = "L1",
        index_codes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        与 GET /django/api/index/sw-valuation-analysis/ 相同实现：按 level 或 index_codes 拉取区间 sw_daily，输出最新一日 PE/PB 及历史分位数。

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            level: 行业分级 L1/L2/L3；未传 index_codes 时使用，默认 L1
            index_codes: 可选，逗号分隔行业 ts_code，优先于 level
        """
        out = run_sw_valuation_analysis(
            start_date,
            end_date,
            level=level,
            index_codes_str=index_codes,
        )
        if out.code != 200:
            return error_payload(out.message, out.code)
        return {
            "code": out.code,
            "message": out.message,
            "timestamp": datetime.now().isoformat(),
            "data": out.data,
        }
