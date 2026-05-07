"""
封装 Tushare 数据获取。

- moneyflow_ind_dc：行业板块资金流向数据
- dc_daily：DC 板块日频行情数据
- bak_daily：备用行情（个股层面日频指标集合）

提供简单调用封装，返回记录列表，供任务模块使用。
"""

import logging
from typing import List, Dict, Optional

from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)


def fetch_dc_industry_moneyflow(
    trade_date: str,
    fields: Optional[str] = None,
) -> List[Dict]:
    """
    获取 Tushare DC 行业板块资金流向数据（moneyflow_ind_dc）。

    Args:
        trade_date: 交易日期，格式 YYYYMMDD
        fields: 可选字段字符串（逗号分隔）。若未提供，默认包含数据库更新需要的全部字段。

    Returns:
        记录列表，每条记录为字典。失败时返回空列表。
    """
    # 默认字段：包含数据库更新所需的主力及各档净流入金额与占比
    default_fields = (
        "trade_date,content_type,name,pct_change,close,net_amount,net_amount_rate,"
        "buy_elg_amount,buy_elg_amount_rate,buy_lg_amount,buy_lg_amount_rate,"
        "buy_md_amount,buy_md_amount_rate,buy_sm_amount,buy_sm_amount_rate,"
        "buy_sm_amount_stock,rank"
    )

    use_fields = fields or default_fields

    params = {
        "trade_date": trade_date,
        "content_type": "行业",
    }

    resp = call_tushare(
        interface="moneyflow_ind_dc",
        params=params,
        fields=use_fields,
        use_query=False,
    )

    if resp.get("code") != 200:
        logger.warning(
            f"调用 Tushare moneyflow_ind_dc 失败: code={resp.get('code')}, msg={resp.get('message')}"
        )
        return []

    data = resp.get("data", {})
    records = data.get("records", [])
    logger.info(f"获取 DC 行业板块资金流向记录数: {len(records)} - trade_date={trade_date}")
    return records


def fetch_dc_daily(
    ts_code: str,
    start_date: str,
    end_date: str,
    fields: Optional[str] = None,
) -> List[Dict]:
    """
    获取 Tushare DC 板块日频数据（dc_daily）。

    Args:
        ts_code: DC 板块代码（例如：BK1036.DC）
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
        fields: 可选字段字符串（逗号分隔）。若未提供，使用接口默认字段。

    Returns:
        记录列表，每条记录为字典。失败时返回空列表。
    """
    params = {
        "ts_code": ts_code,
        "start_date": start_date,
        "end_date": end_date,
    }

    resp = call_tushare(
        interface="dc_daily",
        params=params,
        fields=fields,
        use_query=False,
    )

    if resp.get("code") != 200:
        logger.warning(
            f"调用 Tushare dc_daily 失败: code={resp.get('code')}, msg={resp.get('message')}, ts_code={ts_code}"
        )
        return []

    data = resp.get("data", {})
    records = data.get("records", [])
    logger.info(
        f"获取 DC 板块日频记录数: {len(records)} - ts_code={ts_code}, range={start_date}-{end_date}"
    )
    return records


def fetch_bak_daily(
    trade_date: str,
    fields: Optional[str] = None,
) -> List[Dict]:
    """
    获取 Tushare 备用行情（bak_daily）。

    功能：
    - 拉取指定交易日的全市场个股备用行情数据，包含涨跌幅、价量、量比、换手率、市值等指标。

    参数：
    - trade_date: 交易日期，格式 YYYYMMDD
    - fields: 可选字段字符串（逗号分隔）。不传时使用内置字段集合以满足数据库更新需求。

    返回值：
    - 记录列表，每条记录为字典。失败时返回空列表。

    事件：
    - 调用 common.tushare_proxy.call_tushare 接口
    - 日志记录成功数量或失败信息
    """
    # 默认字段：覆盖代码、名称、价量、涨跌、量比、换手、市值、昨收、行业等
    default_fields = (
        "trade_date,ts_code,name,pct_change,close,change,open,high,low,pre_close,"
        "vol_ratio,turn_over,swing,vol,amount,float_mv,total_mv,pe,industry,area"
    )

    use_fields = fields or default_fields

    params = {
        "trade_date": trade_date,
    }

    resp = call_tushare(
        interface="bak_daily",
        params=params,
        fields=use_fields,
        use_query=False,
    )

    if resp.get("code") != 200:
        logger.warning(
            f"调用 Tushare bak_daily 失败: code={resp.get('code')}, msg={resp.get('message')}, trade_date={trade_date}"
        )
        return []

    data = resp.get("data", {})
    records = data.get("records", [])
    logger.info(
        f"获取备用行情记录数: {len(records)} - trade_date={trade_date}"
    )
    return records