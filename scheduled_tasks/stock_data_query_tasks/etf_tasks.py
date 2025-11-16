"""
ETF 数据采集任务

组件：
- sync_etf_basic：采集并同步 ETF 基本信息到数据库
- update_rt_etf_daily：采集 ETF 实时日线（开盘以来）到数据库（按当日）

依赖：
- Tushare 接口文档：
  - /data/tushare_docs/ETF专题/ETF基本信息.md（接口：etf_basic）
  - /data/tushare_docs/ETF专题/ETF实时日线.md（接口：rt_etf_k）
- 模型存储：etfapp.models.EtfBasic, etfapp.models.EtfDaily
- 统一外部数据调用：common.tushare_proxy.call_tushare

说明：
- 本模块为定时/手动任务，负责从 Tushare 拉取数据并入库；API 层只读数据库，响应格式在 API 统一处理。
"""
import sys
import os
from pathlib import Path
from tracemalloc import start
import django
# 设置Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional

from django.db import transaction

from common.tushare_proxy import call_tushare
from etfapp.models import EtfBasic, EtfDaily


logger = logging.getLogger(__name__)


def _to_date(yyyymmdd: Optional[str]) -> Optional[date]:
    """
    工具：将 YYYYMMDD 字符串转换为 datetime.date

    功能：安全转换，兼容空值或不规范值，失败返回 None
    参数：
    - yyyymmdd (str|None)：日期字符串，格式 YYYYMMDD
    返回值：
    - datetime.date | None
    事件：无
    """
    if not yyyymmdd:
        return None
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d").date()
    except Exception:
        return None


def _to_decimal(val: Any) -> Optional[Decimal]:
    """
    工具：安全转换为 Decimal

    功能：将传入值转换为 Decimal，失败返回 None
    参数：
    - val：任意类型数值或字符串
    返回值：
    - Decimal | None
    事件：无
    """
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def sync_etf_basic(
    list_status: Optional[str] = "L",
    mgr: Optional[str] = None,
    exchange: Optional[str] = None,
    index_code: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    组件：ETF 基本信息采集入库

    功能：
    - 调用 Tushare etf_basic 接口获取 ETF 基本信息
    - 将数据映射并批量新增/更新至 etf_basic 表（EtfBasic 模型）

    参数：
    - list_status (str|None)：上市状态（L上市 D退市 P待上市），默认 'L'
    - mgr (str|None)：基金管理人简称过滤
    - exchange (str|None)：交易所过滤（SH 上交所, SZ 深交所）
    - index_code (str|None)：跟踪指数代码过滤
    - token (str|None)：可选 Tushare Token，覆盖环境变量

    返回值：
    - dict：{"status": "success|warning|error", "message": str, "created": int, "updated": int, "skipped": int}

    事件：
    - 外部数据源调用：common.tushare_proxy.call_tushare('etf_basic')
    - 数据库批处理：bulk_create / bulk_update
    - 日志记录成功数量或失败信息
    """
    logger.info(
        f"开始同步 ETF 基本信息 | list_status={list_status}, mgr={mgr}, exchange={exchange}, index_code={index_code}"
    )

    try:
        params: Dict[str, Any] = {}
        if list_status:
            params["list_status"] = list_status
        if mgr:
            params["mgr"] = mgr
        if exchange:
            params["exchange"] = exchange
        if index_code:
            params["index_code"] = index_code

        # 选择尽可能覆盖模型的字段集合
        fields = (
            "ts_code,csname,extname,cname,index_code,index_name,setup_date,list_date,list_status,"
            "exchange,mgr_name,custod_name,mgt_fee,etf_type"
        )

        resp = call_tushare(
            interface="etf_basic",
            params=params,
            fields=fields,
            token=token,
            use_query=False,
        )

        if resp.get("code") != 200:
            logger.error(f"调用 Tushare 失败: {resp.get('message')} | {resp.get('error')}")
            return {"status": "error", "message": resp.get("message") or "Tushare 调用失败"}

        records: List[Dict[str, Any]] = (resp.get("data") or {}).get("records") or []
        if not records:
            logger.warning("Tushare 返回空记录")
            return {"status": "warning", "message": "Tushare 返回空记录", "created": 0, "updated": 0, "skipped": 0}

        # 准备现有映射
        existing: Dict[str, EtfBasic] = {obj.ts_code: obj for obj in EtfBasic.objects.all()}

        to_create: List[EtfBasic] = []
        to_update: List[EtfBasic] = []
        created_count = 0
        updated_count = 0

        for rec in records:
            try:
                ts_code = str(rec.get("ts_code") or "").strip()
                if not ts_code:
                    continue

                obj = existing.get(ts_code)

                payload = {
                    "csname": rec.get("csname") or None,
                    "extname": rec.get("extname") or "",
                    "cname": rec.get("cname") or None,
                    "index_code": rec.get("index_code") or None,
                    "index_name": rec.get("index_name") or None,
                    "exchange": rec.get("exchange") or None,
                    "list_status": (rec.get("list_status") or "L").strip()[:1],
                    "setup_date": _to_date(rec.get("setup_date")),
                    "list_date": _to_date(rec.get("list_date")),
                    "etf_type": rec.get("etf_type") or None,
                    "mgr_name": rec.get("mgr_name") or None,
                    "custod_name": rec.get("custod_name") or None,
                    "mgt_fee": _to_decimal(rec.get("mgt_fee")),
                }

                if obj:
                    # 更新字段
                    for field, value in payload.items():
                        setattr(obj, field, value)
                    to_update.append(obj)
                else:
                    to_create.append(EtfBasic(ts_code=ts_code, **payload))
            except Exception as e:
                logger.error(f"处理 ETF 基本信息记录失败 ts_code={rec.get('ts_code')}: {str(e)}")
                continue

        # 批量写入
        with transaction.atomic():
            if to_create:
                EtfBasic.objects.bulk_create(to_create, ignore_conflicts=True)
                created_count = len(to_create)
            if to_update:
                EtfBasic.objects.bulk_update(
                    to_update,
                    [
                        "csname",
                        "extname",
                        "cname",
                        "index_code",
                        "index_name",
                        "exchange",
                        "list_status",
                        "setup_date",
                        "list_date",
                        "etf_type",
                        "mgr_name",
                        "custod_name",
                        "mgt_fee",
                    ],
                )
                updated_count = len(to_update)

        logger.info(f"ETF 基本信息同步完成 | created={created_count}, updated={updated_count}")
        return {
            "status": "success",
            "message": "ETF 基本信息同步完成",
            "created": created_count,
            "updated": updated_count,
            "skipped": 0,
        }

    except Exception as e:
        logger.error(f"ETF 基本信息同步失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def update_etf_daily(
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    recent_days: int = 7,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    组件：ETF 日线行情采集入库

    功能：
    - 从 EtfBasic 读取现有 ETF 列表（支持指定单个 ts_code）
    - 调用 Tushare `fund_daily` 接口按日期范围获取日线行情
    - 将数据映射并批量新增/更新至 `etf_daily` 表（EtfDaily 模型）

    参数：
    - ts_code (str|None)：可选，指定某个 ETF 代码，仅抓取该 ETF；默认遍历全部已存在的 ETF
    - start_date (str|None)：开始日期（YYYYMMDD），不传则基于 recent_days 计算
    - end_date (str|None)：结束日期（YYYYMMDD），不传则为当天
    - recent_days (int)：当未提供日期范围时，默认抓取最近 N 天（含当天），默认 7
    - token (str|None)：可选 Tushare Token，覆盖环境变量

    返回值：
    - dict：{"status": "success|partial|error", "message": str, "created": int, "updated": int, "skipped": int, "etf_count": int}

    事件：
    - 外部数据源调用：common.tushare_proxy.call_tushare('fund_daily')
    - 数据库批处理：bulk_create / bulk_update；唯一性校验（ts_code, trade_date）
    - 日志记录成功数量或失败信息
    """
    logger.info(
        f"开始更新 ETF 日线行情 | ts_code={ts_code}, start_date={start_date}, end_date={end_date}, recent_days={recent_days}"
    )

    try:
        # 计算日期范围
        if not end_date:
            end_dt = datetime.now().date()
            end_date = end_dt.strftime("%Y%m%d")
        else:
            try:
                end_dt = datetime.strptime(end_date, "%Y%m%d").date()
            except Exception:
                end_dt = datetime.now().date()

        if not start_date:
            # recent_days 包含当天，因此向前偏移 recent_days-1 天
            from datetime import timedelta
            start_dt = end_dt - timedelta(days=max(recent_days - 1, 0))
            start_date = start_dt.strftime("%Y%m%d")

        # 组装 ETF 列表
        if ts_code:
            etf_codes: List[str] = [ts_code]
        else:
            etf_codes = list(EtfBasic.objects.values_list("ts_code", flat=True))

        if not etf_codes:
            logger.warning("数据库中没有 ETF 基本信息，无法更新日线行情")
            return {"status": "warning", "message": "无 ETF 基本信息", "created": 0, "updated": 0, "skipped": 0, "etf_count": 0}

        total_created = 0
        total_updated = 0
        total_skipped = 0
        error_count = 0

        # 固定字段集合，尽量覆盖 EtfDaily 模型
        fields = (
            "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"
        )

        for code in etf_codes:
            try:
                params: Dict[str, Any] = {
                    "ts_code": code,
                    "start_date": start_date,
                    "end_date": end_date,
                }

                resp = call_tushare(
                    interface="fund_daily",
                    params=params,
                    fields=fields,
                    token=token,
                    use_query=False,
                )

                if resp.get("code") != 200:
                    logger.error(f"调用 Tushare fund_daily 失败: {resp.get('message')} | {resp.get('error')}")
                    error_count += 1
                    continue

                records: List[Dict[str, Any]] = (resp.get("data") or {}).get("records") or []
                if not records:
                    logger.info(f"{code} 在区间 {start_date}~{end_date} 无日线数据")
                    continue

                # 预构建该代码的日期集合（转换为 date）
                date_objs: List[date] = []
                for rec in records:
                    dt_obj = _to_date(str(rec.get("trade_date") or ""))
                    if dt_obj:
                        date_objs.append(dt_obj)

                # 已有记录映射：trade_date -> EtfDaily
                existing_map = {
                    obj.trade_date: obj
                    for obj in EtfDaily.objects.filter(ts_code=code, trade_date__in=date_objs)
                }

                to_create: List[EtfDaily] = []
                to_update: List[EtfDaily] = []

                for rec in records:
                    try:
                        trade_dt = _to_date(str(rec.get("trade_date") or ""))
                        if not trade_dt:
                            total_skipped += 1
                            continue

                        # 安全数值转换
                        open_p = _to_decimal(rec.get("open"))
                        high_p = _to_decimal(rec.get("high"))
                        low_p = _to_decimal(rec.get("low"))
                        close_p = _to_decimal(rec.get("close"))
                        pre_close_p = _to_decimal(rec.get("pre_close"))
                        change_p = _to_decimal(rec.get("change"))
                        pct_chg_p = _to_decimal(rec.get("pct_chg"))

                        vol_val = rec.get("vol")
                        try:
                            vol_int = int(Decimal(str(vol_val))) if vol_val is not None else 0
                        except Exception:
                            vol_int = 0

                        amt_val = _to_decimal(rec.get("amount"))  # 千元
                        # 转为元：amount(千元) * 1000
                        amount_in_yuan = Decimal(0)
                        if amt_val is not None:
                            try:
                                amount_in_yuan = amt_val * Decimal(1000)
                            except Exception:
                                amount_in_yuan = Decimal(0)

                        payload = {
                            "ts_code": code,
                            "trade_date": trade_dt,
                            "open": open_p or Decimal(0),
                            "high": high_p or Decimal(0),
                            "low": low_p or Decimal(0),
                            "close": close_p or Decimal(0),
                            "pre_close": pre_close_p,
                            "change": change_p,
                            "pct_chg": pct_chg_p,
                            "vol": vol_int,
                            "amount": amount_in_yuan,
                        }

                        existing_obj = existing_map.get(trade_dt)
                        if existing_obj:
                            for field, value in payload.items():
                                if field in ("ts_code", "trade_date"):
                                    continue
                                setattr(existing_obj, field, value)
                            to_update.append(existing_obj)
                        else:
                            to_create.append(EtfDaily(**payload))

                    except Exception as e:
                        logger.error(f"处理 ETF {code} {rec.get('trade_date')} 日线记录失败: {str(e)}")
                        total_skipped += 1
                        continue

                # 批量写入数据库
                with transaction.atomic():
                    if to_create:
                        EtfDaily.objects.bulk_create(to_create, ignore_conflicts=True)
                        total_created += len(to_create)
                    if to_update:
                        EtfDaily.objects.bulk_update(
                            to_update,
                            [
                                "open", "high", "low", "close",
                                "pre_close", "change", "pct_chg",
                                "vol", "amount",
                            ],
                        )
                        total_updated += len(to_update)

                logger.info(
                    f"ETF {code} 日线更新完成 | 新增={len(to_create)}, 更新={len(to_update)}, 跳过累计={total_skipped}"
                )

            except Exception as e:
                logger.error(f"ETF {code} 日线更新失败: {str(e)}")
                error_count += 1

        status = "success" if error_count == 0 else "partial"
        message = (
            f"ETF 日线更新任务完成，新增: {total_created}，更新: {total_updated}，跳过: {total_skipped}，失败ETF: {error_count}"
        )
        logger.info(message)
        return {
            "status": status,
            "message": message,
            "created": total_created,
            "updated": total_updated,
            "skipped": total_skipped,
            "etf_count": len(etf_codes),
        }

    except Exception as e:
        logger.error(f"ETF 日线更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    # sync_etf_basic()
    update_etf_daily(recent_days=4000)