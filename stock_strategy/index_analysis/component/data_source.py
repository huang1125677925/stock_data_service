"""
数据源组件：加载申万指数数据

功能：
- 封装从 TuShare 或内部服务加载申万指数历史数据的逻辑；
- 统一输出包含价格与基础指标列的 DataFrame，供特征提取组件使用。

参数：
- ts_codes(list[str]): 申万指数代码列表（如 '801010.SI'）；
- start_date(str): 开始日期，格式 'YYYYMMDD'；
- end_date(str): 结束日期，格式 'YYYYMMDD'；
- fetch_func(callable, 可选): 外部提供的拉取函数，签名为 (api_name, params)->pd.DataFrame；

返回值：
- pandas.DataFrame: 包含列 `ts_code, trade_date, open, high, low, close` 以及可选的 `macd_bfq, macd_dif_bfq, macd_dea_bfq`。

事件：
- 无
"""

from __future__ import annotations

import pandas as pd
from typing import Callable, Iterable

try:
    # 优先使用项目内封装的 TuShare 代理
    from common.tushare_proxy import call_tushare
except Exception:
    call_tushare = None  # 允许在非 Django 环境下导入占位


class SWIndexDataSource:
    """
    申万指数数据源封装

    功能：
    - 按代码与日期范围批量拉取指数日线数据；
    - 兼容外部 fetch 函数，实现可替换的数据提供者（便于测试）。

    参数：
    - fetch_func(callable, 可选): 若提供则使用该函数拉取数据，否则使用 `common.tushare_proxy.call_tushare`。

    返回值：
    - 无（通过成员方法返回 DataFrame）。

    事件：
    - 无
    """

    def __init__(self, fetch_func: Callable | None = None, interface_name: str = "index_daily"):
        """
        初始化数据源

        参数：
        - fetch_func(callable, 可选): 外部抓取函数；默认使用项目内的 `call_tushare`
        - interface_name(str): 接口名称，默认 `index_daily`；申万指数可使用 `sw_daily`

        返回值：
        - 无
        """
        self.fetch_func = fetch_func or call_tushare
        self.interface_name = interface_name

    def load_daily(self, ts_codes: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        拉取申万指数日线数据

        功能：
        - 循环请求 TuShare 指数日线数据，并合并为单一 DataFrame。

        参数：
        - ts_codes(Iterable[str]): 申万指数代码集合；
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'。

        返回值：
        - pandas.DataFrame: 列包含 `ts_code, trade_date, open, high, low, close` 等。

        事件：
        - 无
        """
        if self.fetch_func is None:
            raise RuntimeError("数据源不可用：未找到可用的 fetch 函数。")

        frames: list[pd.DataFrame] = []
        for code in ts_codes:
            # TuShare 指数日线接口名称依据项目封装文档，可通过 interface_name 指定
            params = {
                "ts_code": code,
                "start_date": start_date,
                "end_date": end_date,
            }
            daily_resp = self.fetch_func(self.interface_name, params)
            if daily_resp.get('code') != 200:
                print(f"拉取{code}日线失败: {daily_resp.get('message')}")
                continue
            df = pd.DataFrame(daily_resp.get('data', {}).get('records', []))
            if df.empty:
                continue

            # 统一列名与类型
            df = df.rename(columns={"trade_date": "trade_date"})
            # 确保必须列存在
            required_cols = {"ts_code", "trade_date", "open", "high", "low", "close"}
            missing = required_cols - set(df.columns)
            if missing:
                # 若部分列缺失，尝试补齐为空值以保证下游流程健壮
                for c in missing:
                    df[c] = pd.NA

            frames.append(df[["ts_code", "trade_date", "open", "high", "low", "close"]])

        if not frames:
            return pd.DataFrame(columns=["ts_code", "trade_date", "open", "high", "low", "close"])  # 空结果占位

        out = pd.concat(frames, ignore_index=True)
        out.sort_values(["ts_code", "trade_date"], inplace=True)
        out.reset_index(drop=True, inplace=True)
        return out


    def fetch_sw_index_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        拉取申万指数日线数据

        功能：
        - 封装 `SWIndexDataSource.load_daily` 方法，用于直接调用。

        参数：
        - ts_codes(Iterable[str]): 申万指数代码集合；
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'。

        返回值：
        - pandas.DataFrame: 列包含 `ts_code, trade_date, open, high, low, close` 等。

        事件：
        - 无
        """

        resp = call_tushare(
            interface='index_classify',
            params={'level': 'L3', 'src': 'SW2021'},
            fields='index_code,industry_name,level',
            use_query=False,
        )

        if not isinstance(resp, dict) or resp.get('code') != 200:
            msg = resp.get('message') if isinstance(resp, dict) else str(resp)
            raise RuntimeError(f"获取申万指数分类失败: {msg}")

        records = resp.get('data', {}).get('records', [])
        ts_codes = [r['index_code'] for r in records if isinstance(r, dict) and r.get('index_code')]

        code_map = {r['index_code']: r['industry_name'] for r in records if isinstance(r, dict) and r.get('index_code')}

        return self.load_daily(ts_codes, start_date, end_date), code_map


class IndexDataSource:
    """
    指数数据源封装（基于 `index_basic` 与 `index_daily`）

    功能：
    - 获取通用指数列表（支持市场与类别过滤）；
    - 批量按代码与日期范围拉取指数日线数据；
    - 提供一次性拉取完整数据集的便捷方法（包含代码信息映射）。

    参数：
    - fetch_func(callable, 可选): 若提供则使用该函数拉取数据，否则使用 `common.tushare_proxy.call_tushare`；
    - interface_name(str): 指数日线接口名称，默认 `index_daily`。

    返回值：
    - 无（通过成员方法返回 DataFrame 或 (DataFrame, dict) 元组）。

    事件：
    - 无
    """

    def __init__(self, fetch_func: Callable | None = None, interface_name: str = "index_daily"):
        """
        初始化数据源

        参数：
        - fetch_func(callable, 可选): 外部抓取函数；默认使用项目内的 `call_tushare`；
        - interface_name(str): 接口名称，默认 `index_daily`（指数日线）。

        返回值：
        - 无

        事件：
        - 无
        """
        self.fetch_func = fetch_func or call_tushare
        self.interface_name = interface_name

    def list_index_codes(
        self,
        market: str | None = "SW",
        category: str | None = None,
        limit: int | None = None,
        fields: str = "ts_code,name,market,category",
    ) -> list[dict]:
        """
        获取指数基础信息列表并提取代码集（来自 `index_basic`）

        功能：
        - 调用 TuShare `index_basic` 接口，筛选目标市场/类别的指数，返回统一结构的代码信息列表。

        参数：
        - market(str|None): 市场过滤，如 'SW'/'CSI'/'SSE'/'SZSE' 等，默认 'SW'；
        - category(str|None): 指数类别过滤，默认 None；
        - limit(int|None): 限制返回数量，默认 None（不限制）；
        - fields(str): 返回字段，默认 'ts_code,name,market,category'。

        返回值：
        - list[dict]: 每项为 { 'ts_code': str, 'name': str, 'market': str }。

        事件：
        - 无
        """
        if self.fetch_func is None:
            raise RuntimeError("数据源不可用：未找到可用的 fetch 函数。")

        params: dict = {}
        if market:
            params["market"] = market
        if category:
            params["category"] = category

        resp = self.fetch_func(
            interface="index_basic",
            params=params,
            fields=fields,
            use_query=False,
        )

        if not isinstance(resp, dict) or resp.get("code") != 200:
            msg = resp.get("message") if isinstance(resp, dict) else str(resp)
            raise RuntimeError(f"获取指数基础信息失败: {msg}")

        records = resp.get("data", {}).get("records", [])

        # 限定数量
        if isinstance(limit, int) and limit > 0:
            records = records[:limit]

        code_list: list[dict] = []
        for r in records:
            ts_code = r.get("ts_code")
            if not ts_code:
                continue
            name = r.get("name") or ts_code
            market_val = r.get("market") or "INDEX"
            code_list.append({"ts_code": ts_code, "name": name, "market": market_val})

        return code_list

    def load_daily(self, ts_codes: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        拉取指数日线数据（来自 `index_daily`）

        功能：
        - 循环请求 TuShare 指数日线数据，并合并为单一 DataFrame。

        参数：
        - ts_codes(Iterable[str]): 指数代码集合；
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'。

        返回值：
        - pandas.DataFrame: 列包含 `ts_code, trade_date, open, high, low, close` 等。

        事件：
        - 无
        """
        if self.fetch_func is None:
            raise RuntimeError("数据源不可用：未找到可用的 fetch 函数。")

        frames: list[pd.DataFrame] = []
        for code in ts_codes:
            params = {"ts_code": code, "start_date": start_date, "end_date": end_date}
            daily_resp = self.fetch_func(self.interface_name, params, use_query=False)
            if not isinstance(daily_resp, dict) or daily_resp.get("code") != 200:
                print(f"拉取{code}日线失败: {daily_resp.get('message') if isinstance(daily_resp, dict) else daily_resp}")
                continue
            df = pd.DataFrame(daily_resp.get("data", {}).get("records", []))
            if df.empty:
                continue

            # 统一列名与类型
            df = df.rename(columns={"trade_date": "trade_date"})
            # 确保必须列存在
            required_cols = {"ts_code", "trade_date", "open", "high", "low", "close"}
            missing = required_cols - set(df.columns)
            if missing:
                for c in missing:
                    df[c] = pd.NA

            frames.append(df[["ts_code", "trade_date", "open", "high", "low", "close"]])

        if not frames:
            return pd.DataFrame(columns=["ts_code", "trade_date", "open", "high", "low", "close"])  # 空结果占位

        out = pd.concat(frames, ignore_index=True)
        out.sort_values(["ts_code", "trade_date"], inplace=True)
        out.reset_index(drop=True, inplace=True)
        return out

    def fetch_index_daily_dataset(
        self,
        start_date: str,
        end_date: str,
        market: str | None = "SW",
        category: str | None = None,
        limit: int | None = None,
    ) -> tuple[pd.DataFrame, dict]:
        """
        拉取指数列表与其日线数据集（一次性获取）

        功能：
        - 先查询指数基础信息列表，再批量拉取其日线数据并返回聚合结果。

        参数：
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'；
        - market(str|None): 指数市场过滤，默认 'SW'；
        - category(str|None): 指数类别过滤，默认 None；
        - limit(int|None): 代码数量上限，默认 None。

        返回值：
        - (DataFrame, dict): (聚合日线数据, 代码信息映射 { ts_code: {name, market} })。

        事件：
        - 无
        """
        code_list = self.list_index_codes(market=market, category=category, limit=limit)
        ts_codes = [c["ts_code"] for c in code_list]
        df = self.load_daily(ts_codes, start_date, end_date)
        code_info_map = {c["ts_code"]: {"name": c["name"], "market": c["market"]} for c in code_list}
        return df, code_info_map

    def list_index_codes_from_etf(
        self,
        list_status: str = "L",
        etf_type: str | None = None,
        exchange: str | None = None,
        limit: int | None = None,
        fields: str = "index_code,index_name,exchange,etf_type",
    ) -> list[dict]:
        """
        获取被ETF跟踪的指数列表集合（来自 `etf_basic`）

        功能：
        - 调用 TuShare `etf_basic` 接口，汇总所有ETF的 `index_code/index_name`，去重得到指数列表集合；
        - 返回统一结构，便于后续通过 `index_daily` 拉取这些指数的历史数据。

        参数：
        - list_status(str): ETF 上市状态过滤（L上市 D退市 P待上市），默认 'L'；
        - etf_type(str|None): ETF 类型过滤（如 '境内'/'QDII'），默认 None；
        - exchange(str|None): 交易所过滤（'SH' 或 'SZ'），默认 None；
        - limit(int|None): 限制返回数量，默认 None（不限制）；
        - fields(str): 返回字段，默认 'index_code,index_name,exchange,etf_type'。

        返回值：
        - list[dict]: 每项为 { 'ts_code': str, 'name': str, 'market': str }，其中 'ts_code' 为指数代码（如 '000300.SH'）。

        事件：
        - 无
        """
        if self.fetch_func is None:
            raise RuntimeError("数据源不可用：未找到可用的 fetch 函数。")

        params: dict = {"list_status": list_status}
        if etf_type:
            params["etf_type"] = etf_type
        if exchange:
            params["exchange"] = exchange

        resp = self.fetch_func(
            interface="etf_basic",
            params=params,
            fields=fields,
            use_query=False,
        )

        if not isinstance(resp, dict) or resp.get("code") != 200:
            msg = resp.get("message") if isinstance(resp, dict) else str(resp)
            raise RuntimeError(f"获取ETF基础信息失败: {msg}")

        records = resp.get("data", {}).get("records", [])
        # 过滤掉没有指数代码或名称的记录
        records = [r for r in records if str(r.get("index_code") or "").strip()]

        # 限定数量（针对ETF列表，指数集合仍会去重）
        if isinstance(limit, int) and limit > 0:
            records = records[:limit]

        # 汇总并去重指数代码集合
        code_map: dict[str, dict] = {}
        for r in records:
            idx_code = r.get("index_code")
            idx_name = r.get("index_name") or idx_code
            if not idx_code:
                continue
            # 推断市场
            if str(idx_code).endswith(".SH"):
                market_val = "SSE"
            elif str(idx_code).endswith(".SZ"):
                market_val = "SZSE"
            else:
                market_val = "INDEX"
            code_map[idx_code] = {"ts_code": idx_code, "name": idx_name, "market": market_val}

        return list(code_map.values())

    def fetch_index_daily_dataset_from_etf(
        self,
        start_date: str,
        end_date: str,
        list_status: str = "L",
        etf_type: str | None = None,
        exchange: str | None = None,
        limit: int | None = None,
    ) -> tuple[pd.DataFrame, dict]:
        """
        拉取ETF跟踪的指数集合及其日线数据集（一次性获取）

        功能：
        - 先通过 `etf_basic` 汇总 ETF 跟踪的指数集合，再批量拉取这些指数的 `index_daily` 日线数据并返回聚合结果。

        参数：
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'；
        - list_status(str): ETF 上市状态过滤，默认 'L'；
        - etf_type(str|None): ETF 类型过滤，默认 None；
        - exchange(str|None): 交易所过滤，默认 None；
        - limit(int|None): ETF 数量上限（仅用于限制ETF列表），默认 None。

        返回值：
        - (DataFrame, dict): (聚合日线数据, 代码信息映射 { ts_code: {name, market} })。

        事件：
        - 无
        """
        code_list = self.list_index_codes_from_etf(
            list_status=list_status,
            etf_type=etf_type,
            exchange=exchange,
            limit=limit,
        )
        ts_codes = [c["ts_code"] for c in code_list]
        df = self.load_daily(ts_codes, start_date, end_date)
        code_info_map = {c["ts_code"]: {"name": c["name"], "market": c["market"]} for c in code_list}
        return df, code_info_map


class ETFDataSource:
    """
    ETF 数据源封装

    功能：
    - 拉取 ETF 基础信息（代码、名称、交易所），并提供批量代码列表；
    - 按代码与日期范围批量拉取 ETF 日线数据；
    - 兼容外部 fetch 函数，实现可替换的数据提供者（便于测试）。

    参数：
    - fetch_func(callable, 可选): 若提供则使用该函数拉取数据，否则使用 `common.tushare_proxy.call_tushare`。
    - interface_name(str): ETF 日线接口名称，默认 `fund_daily`。

    返回值：
    - 无（通过成员方法返回 DataFrame 或(数据,元信息)元组）。

    事件：
    - 无
    """

    def __init__(self, fetch_func: Callable | None = None, interface_name: str = "fund_daily"):
        """
        初始化数据源

        参数：
        - fetch_func(callable, 可选): 外部抓取函数；默认使用项目内的 `call_tushare`
        - interface_name(str): 接口名称，默认 `fund_daily`（ETF 日线）

        返回值：
        - 无
        """
        self.fetch_func = fetch_func or call_tushare
        self.interface_name = interface_name

    def list_etf_codes(
        self,
        list_status: str = "L",
        etf_type: str | None = "境内",
        limit: int | None = None,
        fields: str = "ts_code,extname,index_name,exchange",
    ) -> list[dict]:
        """
        获取 ETF 基础信息列表并提取代码集

        功能：
        - 调用 Tushare `etf_basic` 接口，筛选上市 ETF，返回统一结构的代码信息列表。

        参数：
        - list_status(str): 上市状态（L上市 D退市 P待上市），默认 L；
        - etf_type(str|None): ETF 类型过滤（如 '境内'），默认 '境内'；
        - limit(int|None): 限制返回数量，默认 None（不限制）；
        - fields(str): 返回字段，默认 'ts_code,extname,index_name,exchange'。

        返回值：
        - list[dict]: 每项为 { 'ts_code': str, 'name': str, 'market': str }。

        事件：
        - 无
        """
        if self.fetch_func is None:
            raise RuntimeError("数据源不可用：未找到可用的 fetch 函数。")

        resp = self.fetch_func(
            interface="etf_basic",
            params={"list_status": list_status, **({"etf_type": etf_type} if etf_type else {})},
            fields=fields,
            use_query=False,
        )

        if not isinstance(resp, dict) or resp.get("code") != 200:
            msg = resp.get("message") if isinstance(resp, dict) else str(resp)
            raise RuntimeError(f"获取ETF基础信息失败: {msg}")

        records = resp.get("data", {}).get("records", [])
        # 过滤无指数名称的记录，统一字段
        records = [r for r in records if str(r.get("index_name") or "").strip()]

        # 限定数量
        if isinstance(limit, int) and limit > 0:
            records = records[:limit]

        code_list: list[dict] = []
        for r in records:
            ts_code = r.get("ts_code")
            if not ts_code:
                continue
            name = r.get("extname") or r.get("index_name") or ts_code
            # 推断市场（交易所）
            if ts_code.endswith(".SH"):
                market = "SSE"
            elif ts_code.endswith(".SZ"):
                market = "SZSE"
            else:
                market = r.get("exchange") or "ETF"
            code_list.append({"ts_code": ts_code, "name": name, "market": market})

        return code_list

    def load_daily(self, ts_codes: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        拉取 ETF 日线数据

        功能：
        - 循环请求 TuShare ETF 日线数据，并合并为单一 DataFrame。

        参数：
        - ts_codes(Iterable[str]): ETF 代码集合；
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'。

        返回值：
        - pandas.DataFrame: 列包含 `ts_code, trade_date, open, high, low, close` 等。

        事件：
        - 无
        """
        if self.fetch_func is None:
            raise RuntimeError("数据源不可用：未找到可用的 fetch 函数。")

        frames: list[pd.DataFrame] = []
        for code in ts_codes:
            params = {"ts_code": code, "start_date": start_date, "end_date": end_date}
            daily_resp = self.fetch_func(self.interface_name, params, use_query=False)
            if not isinstance(daily_resp, dict) or daily_resp.get("code") != 200:
                print(f"拉取{code}日线失败: {daily_resp.get('message') if isinstance(daily_resp, dict) else daily_resp}")
                continue
            df = pd.DataFrame(daily_resp.get("data", {}).get("records", []))
            if df.empty:
                continue

            # 统一列名与类型
            df = df.rename(columns={"trade_date": "trade_date"})
            # 确保必须列存在
            required_cols = {"ts_code", "trade_date", "open", "high", "low", "close"}
            missing = required_cols - set(df.columns)
            if missing:
                for c in missing:
                    df[c] = pd.NA
            time.sleep(0.01)  # 避免请求过快

            frames.append(df[["ts_code", "trade_date", "open", "high", "low", "close"]])

        if not frames:
            return pd.DataFrame(columns=["ts_code", "trade_date", "open", "high", "low", "close"])  # 空结果占位

        out = pd.concat(frames, ignore_index=True)
        out.sort_values(["ts_code", "trade_date"], inplace=True)
        out.reset_index(drop=True, inplace=True)
        return out

    def fetch_etf_daily_dataset(
        self,
        start_date: str,
        end_date: str,
        list_status: str = "L",
        etf_type: str | None = "境内",
        limit: int | None = None,
    ) -> tuple[pd.DataFrame, dict]:
        """
        拉取 ETF 列表与其日线数据集

        功能：
        - 先查询 ETF 基础信息列表，再批量拉取其日线数据并返回聚合结果。

        参数：
        - start_date(str): 开始日期 'YYYYMMDD'；
        - end_date(str): 结束日期 'YYYYMMDD'；
        - list_status(str): 上市状态过滤，默认 'L'；
        - etf_type(str|None): ETF 类型过滤，默认 '境内'；
        - limit(int|None): 代码数量上限，默认 None。

        返回值：
        - (DataFrame, dict): (聚合日线数据, 代码信息映射 { ts_code: {name, market} })。

        事件：
        - 无
        """
        code_list = self.list_etf_codes(list_status=list_status, etf_type=etf_type, limit=limit)
        ts_codes = [c["ts_code"] for c in code_list]
        df = self.load_daily(ts_codes, start_date, end_date)
        code_info_map = {c["ts_code"]: {"name": c["name"], "market": c["market"]} for c in code_list}
        return df, code_info_map
