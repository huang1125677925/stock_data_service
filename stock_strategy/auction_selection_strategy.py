import json
import logging
import math
import os
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class AuctionSelectionStrategyService:
    """
    组件：9点25竞价选股策略服务（AuctionSelectionStrategyService）

    功能：
    - 基于前一交易日涨停数据与目标交易日集合竞价数据，筛选符合条件的竞价候选股。
    - 计算个股评分、市场情绪、首选池/观察池，并输出适合前端展示的结构化结果。

    参数：
    - tushare_pro (object，可选): 外部传入的 Tushare pro 客户端，便于测试或复用。
    - sleep_func (Callable，可选): 重试等待函数，默认 `time.sleep`，测试时可传入空函数。

    返回值：
    - `get_strategy_result()` 返回包含市场情绪、候选池、TOP池、评分拆解和查询参数的字典。

    事件：
    - 交易日、涨停池、竞价数据获取失败时记录日志并抛出异常。
    - 竞价数据为空时按指数退避策略重试，适用于 9:25 后数据延迟更新场景。
    """

    def __init__(self, tushare_pro: Any = None, sleep_func: Optional[Callable[[float], None]] = None):
        self._tushare_pro = tushare_pro
        self._sleep_func = sleep_func or time.sleep

    def get_strategy_result(
        self,
        trade_date: Optional[str] = None,
        top_n: int = 3,
        token: Optional[str] = None,
        auction_max_retries: int = 12,
        auction_base_wait: int = 5,
        prev_limit_max_retries: int = 3,
        prev_limit_base_wait: int = 3,
    ) -> Dict[str, Any]:
        """
        功能：执行 9 点 25 竞价选股策略，并返回前端可直接使用的结构化数据。

        参数：
        - trade_date (str，可选): 目标交易日，格式 `YYYYMMDD`；为空时自动取最近交易日。
        - top_n (int，可选): 返回的首选池数量，默认 3。
        - token (str，可选): Tushare Token，优先级高于环境变量。
        - auction_max_retries (int，可选): 竞价数据最大重试次数。
        - auction_base_wait (int，可选): 竞价数据基础重试等待秒数。
        - prev_limit_max_retries (int，可选): 昨日涨停数据最大重试次数。
        - prev_limit_base_wait (int，可选): 昨日涨停数据基础重试等待秒数。

        返回值：
        - dict: 包含 `summary`、`market_sentiment`、`top_candidates`、`candidates`、`params` 等字段。

        异常：
        - ValueError: 当日期格式错误、日期不是交易日或参数非法时抛出。
        - RuntimeError: 当 Tushare Token 缺失、接口初始化失败或关键数据无法获取时抛出。
        """
        if top_n <= 0:
            raise ValueError("top_n 必须大于 0")

        if trade_date:
            self._validate_trade_date(trade_date)

        pro = self._get_tushare_pro(token=token)
        recent_days = self.get_recent_trade_days(pro=pro, target_date=trade_date)
        target_date = trade_date or recent_days[-1]

        if target_date not in recent_days:
            raise ValueError(f"日期 {target_date} 不是有效交易日")

        target_index = recent_days.index(target_date)
        if target_index <= 0:
            raise RuntimeError(f"日期 {target_date} 缺少前一交易日数据")

        prev_trade_date = recent_days[target_index - 1]

        prev_limit_df = self.fetch_with_retry(
            fetcher=lambda: pro.limit_list_d(
                trade_date=prev_trade_date,
                limit_type="U",
                fields="trade_date,ts_code,name,float_mv,amount,fd_amount,open_times,last_time,limit_times",
            ),
            data_name="昨日涨停",
            max_retries=prev_limit_max_retries,
            base_wait=prev_limit_base_wait,
        )
        if prev_limit_df is None:
            raise RuntimeError("无法获取昨日涨停数据")

        auction_df = self.fetch_with_retry(
            fetcher=lambda: pro.stk_auction(
                trade_date=target_date,
                fields="ts_code,trade_date,price,pre_close,amount",
            ),
            data_name="集合竞价",
            max_retries=auction_max_retries,
            base_wait=auction_base_wait,
        )
        if auction_df is None:
            raise RuntimeError("竞价数据多次重试后仍为空，可能今日非交易日或接口异常")

        auction_map = self.build_auction_map(auction_df)
        candidates = self.build_candidates(prev_limit_df, auction_map)
        top_candidates = candidates[:top_n]
        market_sentiment = self.build_market_sentiment(prev_limit_df=prev_limit_df, top_candidates=top_candidates)

        return {
            "summary": self.build_summary(target_date=target_date, top_candidates=top_candidates, market_sentiment=market_sentiment),
            "market_sentiment": market_sentiment,
            "top_candidates": top_candidates,
            "candidates": candidates,
            "statistics": {
                "candidate_pool_size": int(prev_limit_df["ts_code"].nunique()) if "ts_code" in prev_limit_df.columns else len(prev_limit_df),
                "matched_auction_count": len(auction_map),
                "selected_count": len(candidates),
                "top_count": len(top_candidates),
            },
            "params": {
                "trade_date": target_date,
                "prev_trade_date": prev_trade_date,
                "top_n": top_n,
                "auction_max_retries": auction_max_retries,
                "auction_base_wait": auction_base_wait,
                "prev_limit_max_retries": prev_limit_max_retries,
                "prev_limit_base_wait": prev_limit_base_wait,
            },
            "query_time": datetime.now().isoformat(),
        }

    def get_recent_trade_days(self, pro: Any, target_date: Optional[str] = None) -> List[str]:
        """
        功能：获取目标日期附近的最近交易日列表，用于定位目标日和前一交易日。

        参数：
        - pro (object): Tushare pro 客户端。
        - target_date (str，可选): 目标交易日，格式 `YYYYMMDD`。

        返回值：
        - list[str]: 升序排列的交易日列表，至少包含目标日之前的若干交易日。

        异常：
        - RuntimeError: 当交易日历为空时抛出。
        """
        end_date = datetime.strptime(target_date, "%Y%m%d") if target_date else datetime.now()
        start_date = end_date - timedelta(days=40)
        calendar_df = pro.trade_cal(
            exchange="",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            fields="cal_date,is_open",
        )

        if calendar_df is None or calendar_df.empty:
            raise RuntimeError("无法获取交易日历")

        open_days = calendar_df[calendar_df["is_open"] == 1]["cal_date"].astype(str).tolist()
        open_days.sort()
        if not open_days:
            raise RuntimeError("交易日历中未找到有效交易日")

        return open_days[-5:] if not target_date else open_days

    def fetch_with_retry(
        self,
        fetcher: Callable[[], Optional[pd.DataFrame]],
        data_name: str,
        max_retries: int = 6,
        base_wait: int = 5,
    ) -> Optional[pd.DataFrame]:
        """
        功能：按指数退避策略重试拉取外部数据，适配竞价数据短时延迟场景。

        参数：
        - fetcher (Callable): 实际执行数据拉取的函数，应返回 `DataFrame` 或 `None`。
        - data_name (str): 数据名称，用于日志记录。
        - max_retries (int，可选): 最大重试次数。
        - base_wait (int，可选): 基础等待秒数。

        返回值：
        - DataFrame | None: 获取成功时返回非空 DataFrame，失败时返回 `None`。

        异常：
        - 本函数内部吞掉重试过程中的临时异常，仅在日志中记录，不主动抛出。
        """
        for attempt in range(1, max_retries + 1):
            try:
                result = fetcher()
                if result is not None and not result.empty:
                    return result
                logger.warning("%s 数据为空，当前重试次数 %s/%s", data_name, attempt, max_retries)
            except Exception as exc:
                logger.warning("%s 获取失败，当前重试次数 %s/%s，异常: %s", data_name, attempt, max_retries, exc)

            if attempt < max_retries:
                wait_seconds = base_wait * (1.5 ** (attempt - 1))
                self._sleep_func(wait_seconds)

        return None

    def build_auction_map(self, auction_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        功能：将集合竞价原始数据转换为按股票代码索引的映射，便于后续快速筛选。

        参数：
        - auction_df (DataFrame): Tushare `stk_auction` 返回数据。

        返回值：
        - dict: 键为 `ts_code`，值包含竞价价格、竞价涨幅、竞价金额、昨收价等信息。

        异常：
        - 无；异常行会被跳过并记录调试日志。
        """
        auction_map: Dict[str, Dict[str, float]] = {}
        for _, row in auction_df.iterrows():
            try:
                code = str(row["ts_code"])
                price = self.safe_float(row.get("price"))
                pre_close = self.safe_float(row.get("pre_close"))
                amount = self.safe_float(row.get("amount"))
                if not code or pre_close <= 0 or price <= 0:
                    continue

                gap_pct = (price / pre_close - 1) * 100
                auction_map[code] = {
                    "auction_price": round(price, 3),
                    "pre_close": round(pre_close, 3),
                    "auction_amount": round(amount, 2),
                    "gap_pct": round(gap_pct, 3),
                }
            except Exception as exc:
                logger.debug("构建竞价映射时跳过异常行: %s", exc)

        return auction_map

    def build_candidates(self, prev_limit_df: pd.DataFrame, auction_map: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        功能：对昨日涨停池逐只应用竞价筛选条件，并输出带评分拆解的候选列表。

        参数：
        - prev_limit_df (DataFrame): 前一交易日涨停数据。
        - auction_map (dict): 由 `build_auction_map()` 生成的竞价映射。

        返回值：
        - list[dict]: 按最终评分倒序排列的候选股列表。

        异常：
        - 无；个别异常行会跳过并记录调试日志。
        """
        candidates: List[Dict[str, Any]] = []

        for _, row in prev_limit_df.iterrows():
            try:
                candidate = self.build_candidate(row=row, auction_map=auction_map)
                if candidate is not None:
                    candidates.append(candidate)
            except Exception as exc:
                logger.debug("构建候选股时跳过异常行: %s", exc)

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates

    def build_candidate(self, row: pd.Series, auction_map: Dict[str, Dict[str, float]]) -> Optional[Dict[str, Any]]:
        """
        功能：对单只昨日涨停股票执行过滤与打分，返回前端可展示的候选结果。

        参数：
        - row (Series): 单只股票的昨日涨停数据。
        - auction_map (dict): 竞价映射数据。

        返回值：
        - dict | None: 满足条件时返回候选结果；不满足筛选条件时返回 `None`。

        异常：
        - 无；异常由上层统一处理。
        """
        code = str(row.get("ts_code", ""))
        name = str(row.get("name", ""))
        if not code or "ST" in name or code.endswith(".BJ"):
            return None
        if code not in auction_map:
            return None

        float_mv = self.safe_float(row.get("float_mv"))
        float_mv_billion = float_mv / 1e4 if float_mv > 0 else 0
        if float_mv_billion < 20:
            return None

        auction_info = auction_map[code]
        gap_pct = auction_info["gap_pct"]
        if gap_pct < -3:
            return None

        auction_amount = auction_info["auction_amount"]
        volume_ratio_pct = auction_amount / float_mv * 100 if float_mv > 0 else 0
        if volume_ratio_pct < 0.05:
            return None

        limit_times = int(self.safe_float(row.get("limit_times"), default=1))
        prev_amount = self.safe_float(row.get("amount"))
        fd_amount = self.safe_float(row.get("fd_amount"))
        open_times = int(self.safe_float(row.get("open_times"), default=0))
        last_time = str(row.get("last_time", "") or "")
        limit_seal_ratio_pct = fd_amount / prev_amount * 100 if prev_amount > 0 else 0
        if limit_seal_ratio_pct < 5:
            return None

        is_weak_to_strong = self.is_weak_to_strong(open_times=open_times, last_time=last_time)
        score_result = self.calculate_score(
            float_mv_billion=float_mv_billion,
            gap_pct=gap_pct,
            volume_ratio_pct=volume_ratio_pct,
            limit_times=limit_times,
            limit_seal_ratio_pct=limit_seal_ratio_pct,
            is_weak_to_strong=is_weak_to_strong,
        )
        if score_result["final_score"] < 16:
            return None

        return {
            "name": name,
            "code": code,
            "score": score_result["final_score"],
            "auction_price": auction_info["auction_price"],
            "pre_close": auction_info["pre_close"],
            "auction_amount": auction_amount,
            "gap_pct": round(gap_pct, 2),
            "limit_times": limit_times,
            "volume_ratio_pct": round(volume_ratio_pct, 3),
            "float_mv_billion": round(float_mv_billion, 2),
            "limit_seal_ratio_pct": round(limit_seal_ratio_pct, 2),
            "open_times": open_times,
            "last_time": last_time,
            "is_weak_to_strong": is_weak_to_strong,
            "score_breakdown": score_result,
        }

    def calculate_score(
        self,
        float_mv_billion: float,
        gap_pct: float,
        volume_ratio_pct: float,
        limit_times: int,
        limit_seal_ratio_pct: float,
        is_weak_to_strong: bool,
    ) -> Dict[str, float]:
        """
        功能：根据竞价强度、板位、量能和风险因子，对单只股票进行拆项评分。

        参数：
        - float_mv_billion (float): 流通市值，单位亿元。
        - gap_pct (float): 竞价涨幅，单位百分比。
        - volume_ratio_pct (float): 竞价金额相对流通市值的占比，单位百分比。
        - limit_times (int): 连板数。
        - limit_seal_ratio_pct (float): 前一日封单额占成交额比例，单位百分比。
        - is_weak_to_strong (bool): 是否弱转强。

        返回值：
        - dict: 包含各评分项、风险扣分、原始分与最终分。

        异常：
        - 无。
        """
        if float_mv_billion > 200:
            auction_volume_score = 5 if volume_ratio_pct >= 0.5 else 4 if volume_ratio_pct >= 0.3 else 4 if volume_ratio_pct >= 0.2 else 3 if volume_ratio_pct >= 0.1 else 2
        else:
            auction_volume_score = 5 if volume_ratio_pct >= 0.5 else 4 if volume_ratio_pct >= 0.3 else 3 if volume_ratio_pct >= 0.2 else 2 if volume_ratio_pct >= 0.1 else 1
        if volume_ratio_pct > 1.0:
            auction_volume_score -= 0.5

        if 8 <= gap_pct < 10:
            gap_score = 5
        elif gap_pct >= 10:
            gap_score = 4.5
        elif 3 <= gap_pct < 8:
            gap_score = 4
        elif gap_pct >= 1:
            gap_score = 3
        elif gap_pct >= -0.5:
            gap_score = 3
        else:
            gap_score = 2

        board_height_score = 4.5 if limit_times == 3 else 4 if limit_times == 2 else 2.5 if limit_times == 1 else 2
        premium_score = 4

        if limit_times >= 2 and gap_pct >= 6 and volume_ratio_pct > 0.3:
            continuation_score = 5 if not is_weak_to_strong else 4
        elif limit_times >= 2 and gap_pct >= 4:
            continuation_score = 4 if not is_weak_to_strong else 3
        elif limit_times >= 2 and gap_pct >= 1:
            continuation_score = 2
        elif limit_times >= 2:
            continuation_score = 2
        elif limit_times == 1 and gap_pct >= 6:
            continuation_score = 3
        elif limit_times == 1 and gap_pct >= 3:
            continuation_score = 2.5
        elif limit_times == 1 and gap_pct >= 1:
            continuation_score = 2
        else:
            continuation_score = 2

        risk_penalty = 0.0
        if limit_seal_ratio_pct < 10:
            risk_penalty += 2
        elif limit_seal_ratio_pct < 30:
            risk_penalty += 1.5
        elif limit_seal_ratio_pct < 50:
            risk_penalty += 0.5

        if limit_times >= 4:
            risk_penalty += 2
        if limit_times >= 3 and gap_pct < 2:
            risk_penalty += 1
        if float_mv_billion >= 500:
            risk_penalty -= 1
        elif float_mv_billion >= 200:
            risk_penalty -= 0.5
        if is_weak_to_strong:
            risk_penalty += 0.5

        raw_score = (
            auction_volume_score * 0.25
            + gap_score * 0.20
            + board_height_score * 0.15
            + premium_score * 0.20
            + continuation_score * 0.20
        )
        final_score = raw_score * 4 - risk_penalty

        return {
            "auction_volume_score": round(auction_volume_score, 2),
            "gap_score": round(gap_score, 2),
            "board_height_score": round(board_height_score, 2),
            "premium_score": round(premium_score, 2),
            "continuation_score": round(continuation_score, 2),
            "risk_penalty": round(risk_penalty, 2),
            "raw_score": round(raw_score, 2),
            "final_score": round(final_score, 1),
        }

    def build_market_sentiment(self, prev_limit_df: pd.DataFrame, top_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        功能：根据昨日涨停池数据生成市场情绪判断与结论文本。

        参数：
        - prev_limit_df (DataFrame): 前一交易日涨停数据。
        - top_candidates (list[dict]): 已排序的候选池前 N 项。

        返回值：
        - dict: 包含最高板、3进4晋级率、阶段标签、标题和结论文本。

        异常：
        - 无。
        """
        limit_times_series = prev_limit_df["limit_times"] if "limit_times" in prev_limit_df.columns else pd.Series(dtype=float)
        max_limit_times = int(limit_times_series.fillna(1).max()) if not limit_times_series.empty else 0
        third_board_count = int((limit_times_series.fillna(0) == 3).sum()) if not limit_times_series.empty else 0
        fourth_board_count = int((limit_times_series.fillna(0) == 4).sum()) if not limit_times_series.empty else 0
        advance_rate_3_to_4 = round(fourth_board_count / third_board_count * 100, 2) if third_board_count > 0 else 0.0
        is_defense = advance_rate_3_to_4 < 20 or max_limit_times < 3

        conclusion = "退潮防守期，今日不推荐接力"
        if not is_defense:
            conclusion = "可操作，优先关注评分最高的竞价候选股"
        elif top_candidates:
            conclusion = f"退潮防守期，不建议直接接力，可关注 {', '.join(item['name'] for item in top_candidates[:3])} 的 9:30 后承接"

        return {
            "max_limit_times": max_limit_times,
            "third_board_count": third_board_count,
            "fourth_board_count": fourth_board_count,
            "advance_rate_3_to_4": advance_rate_3_to_4,
            "phase": "defense" if is_defense else "attack",
            "phase_label": "退潮防守期" if is_defense else "市场友好期",
            "section_title": "观察池" if is_defense else "首选买入池",
            "conclusion": conclusion,
        }

    def build_summary(self, target_date: str, top_candidates: List[Dict[str, Any]], market_sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        功能：汇总最终展示摘要，供前端头部卡片或结论模块直接使用。

        参数：
        - target_date (str): 目标交易日，格式 `YYYYMMDD`。
        - top_candidates (list[dict]): TOP 候选股列表。
        - market_sentiment (dict): 市场情绪结果。

        返回值：
        - dict: 包含标题、副标题、首选标的和风险提示。

        异常：
        - 无。
        """
        best_candidate = top_candidates[0] if top_candidates else None
        return {
            "title": f"{target_date} 9点25竞价选股结果",
            "subtitle": market_sentiment["phase_label"],
            "best_candidate": best_candidate,
            "risk_warning": "仅策略研究，不构成投资建议",
        }

    def is_weak_to_strong(self, open_times: int, last_time: str) -> bool:
        """
        功能：根据开板次数与最后封板时间判断个股是否属于弱转强模式。

        参数：
        - open_times (int): 开板次数。
        - last_time (str): 最后封板时间，常见格式为 `143015` 等数字字符串。

        返回值：
        - bool: `True` 表示判定为弱转强，`False` 表示非弱转强。

        异常：
        - 无；时间解析失败时默认返回 `False`。
        """
        last_time_value = self.parse_time_to_int(last_time)
        return open_times >= 2 or last_time_value > 143000

    def _get_tushare_pro(self, token: Optional[str] = None) -> Any:
        """
        功能：获取 Tushare pro 客户端，优先复用注入实例，其次按 token 初始化。

        参数：
        - token (str，可选): 显式传入的 Tushare Token。

        返回值：
        - object: Tushare pro 客户端实例。

        异常：
        - RuntimeError: 当 tushare 未安装、token 缺失或初始化失败时抛出。
        """
        if self._tushare_pro is not None:
            return self._tushare_pro

        resolved_token = self.resolve_tushare_token(token=token)
        if not resolved_token:
            raise RuntimeError("未找到 TUSHARE_TOKEN，请先配置环境变量或 openclaw 配置文件")

        try:
            import tushare as ts
        except Exception as exc:
            raise RuntimeError(f"导入 tushare 失败: {exc}") from exc

        try:
            ts.set_token(resolved_token)
        except Exception:
            logger.debug("执行 ts.set_token 失败，继续尝试通过 pro_api(token) 初始化")

        try:
            return ts.pro_api(resolved_token)
        except Exception as exc:
            raise RuntimeError(f"初始化 Tushare 接口失败: {exc}") from exc

    def resolve_tushare_token(self, token: Optional[str] = None) -> Optional[str]:
        """
        功能：解析 Tushare Token，优先使用显式参数，其次读取环境变量和本地配置文件。

        参数：
        - token (str，可选): 显式传入的 Token。

        返回值：
        - str | None: 成功返回 Token，失败返回 `None`。

        异常：
        - 无；配置文件读取失败时仅记录调试日志。
        """
        if token:
            return token

        env_token = os.environ.get("TUSHARE_TOKEN")
        if env_token:
            return env_token

        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if not os.path.exists(config_path):
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config = json.load(file)
            return (
                config.get("skills", {})
                .get("entries", {})
                .get("tushare-data", {})
                .get("env", {})
                .get("TUSHARE_TOKEN")
            )
        except Exception as exc:
            logger.debug("读取本地 openclaw 配置失败: %s", exc)
            return None

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """
        功能：将任意值安全转换为浮点数，统一处理空值、NaN 和非法值。

        参数：
        - value (Any): 待转换值。
        - default (float，可选): 转换失败时返回的默认值。

        返回值：
        - float: 转换后的浮点数。

        异常：
        - 无。
        """
        try:
            result = float(value)
            if math.isnan(result):
                return default
            return result
        except (TypeError, ValueError):
            return default

    @staticmethod
    def parse_time_to_int(value: Any) -> int:
        """
        功能：将封板时间等字段解析为整数时间值，便于比较。

        参数：
        - value (Any): 原始时间值，支持字符串、数字或空值。

        返回值：
        - int: 解析后的整数形式时间；解析失败返回 0。

        异常：
        - 无。
        """
        if value is None:
            return 0

        time_text = "".join(ch for ch in str(value) if ch.isdigit())
        return int(time_text) if time_text else 0

    @staticmethod
    def _validate_trade_date(trade_date: str) -> None:
        """
        功能：校验交易日参数格式是否为 `YYYYMMDD`。

        参数：
        - trade_date (str): 待校验日期字符串。

        返回值：
        - None

        异常：
        - ValueError: 当日期格式非法时抛出。
        """
        if len(trade_date) != 8 or not trade_date.isdigit():
            raise ValueError("trade_date 参数格式错误，应为 YYYYMMDD")


auction_selection_strategy_service = AuctionSelectionStrategyService()
