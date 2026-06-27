#!/usr/bin/env python3
"""
导出东方财富板块成分快照脚本。

功能：
- 使用 Tushare `dc_index` 获取最新交易日的东方财富板块列表
- 使用 Tushare `dc_member` 获取每个板块在最新交易日的成分股
- 将板块与成分股快照导出为本地 JSON 文件，供行业宽度接口优先读取

参数：
- 通过命令行参数传入 token、输出文件路径、板块类型过滤等信息

返回值：
- 成功时返回 0
- 失败时返回非 0 状态码

异常：
- 网络异常、认证失败、文件写入失败时抛出异常并由主流程捕获
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import tushare as ts


DEFAULT_OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "dc_board_members_snapshot.json"
)


def normalize_text(value: object) -> str:
    """标准化文本字段，避免将 NaN 等无效值写入 JSON。

    参数：
    - value (object): 原始字段值。

    返回值：
    - str: 去空白后的字符串；当值为空或为 NaN 时返回空字符串。

    异常：
    - 无。
    """
    text = str(value or "").strip()
    if text.lower() == "nan":
        return ""
    return text


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    参数：
    - 无。

    返回值：
    - argparse.Namespace: 解析后的命令行参数对象。

    异常：
    - argparse 在参数不合法时会自行抛出异常并退出。
    """
    parser = argparse.ArgumentParser(description="导出东方财富板块成分快照到 JSON 文件")
    parser.add_argument("--token", required=True, help="Tushare Token")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_FILE),
        help="输出 JSON 文件路径，默认写入 data/dc_board_members_snapshot.json",
    )
    parser.add_argument(
        "--idx-type",
        dest="idx_type",
        default="",
        help="可选，指定东方财富板块类型，例如 行业板块、概念板块、地域板块；为空则导出全部",
    )
    parser.add_argument(
        "--sleep-seconds",
        dest="sleep_seconds",
        type=float,
        default=0.2,
        help="每次 dc_member 请求之间的休眠秒数，默认 0.2，用于规避接口限频",
    )
    return parser.parse_args()


def get_latest_trade_date(pro) -> str:
    """获取东方财富板块的最新交易日。

    参数：
    - pro: Tushare Pro 客户端对象。

    返回值：
    - str: 最新交易日，格式 YYYYMMDD。

    异常：
    - RuntimeError: 当未获取到任何有效交易日时抛出。
    """
    df = pro.dc_index(fields="ts_code,trade_date,idx_type,level,name")
    if df is None or df.empty:
        raise RuntimeError("未获取到 dc_index 数据，无法确定最新交易日")
    dates = [str(item).strip() for item in df["trade_date"].tolist() if str(item).strip()]
    if not dates:
        raise RuntimeError("dc_index 数据中缺少 trade_date，无法确定最新交易日")
    return max(dates)


def fetch_board_rows(pro, trade_date: str, idx_type: Optional[str] = None) -> List[Dict]:
    """获取指定交易日的东方财富板块列表。

    参数：
    - pro: Tushare Pro 客户端对象。
    - trade_date (str): 交易日，格式 YYYYMMDD。
    - idx_type (Optional[str]): 板块类型过滤；为空时导出全部。

    返回值：
    - List[Dict]: 板块记录列表。

    异常：
    - 无。若未获取到数据则返回空列表。
    """
    params: Dict[str, str] = {"trade_date": trade_date}
    if idx_type:
        params["idx_type"] = idx_type
    df = pro.dc_index(**params, fields="ts_code,trade_date,name,idx_type,level")
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def fetch_members_for_board(
    pro,
    trade_date: str,
    board_code: str,
    sleep_seconds: float = 0.2,
    max_retries: int = 3,
) -> List[str]:
    """获取指定板块在某个交易日的成分股代码列表。

    参数：
    - pro: Tushare Pro 客户端对象。
    - trade_date (str): 交易日，格式 YYYYMMDD。
    - board_code (str): 板块代码。
    - sleep_seconds (float): 单次请求后休眠秒数。
    - max_retries (int): 单个板块请求失败时的最大重试次数。

    返回值：
    - List[str]: 成分股代码列表，格式为 Tushare `ts_code`。

    异常：
    - 无。单个板块获取失败时返回空列表。
    """
    for attempt in range(max_retries):
        try:
            df = pro.dc_member(
                trade_date=trade_date,
                ts_code=board_code,
                fields="trade_date,ts_code,con_code,name",
            )
            time.sleep(max(sleep_seconds, 0))
            if df is None or df.empty:
                return []
            codes = []
            for item in df["con_code"].tolist():
                normalized = str(item).strip()
                if normalized:
                    codes.append(normalized)
            return sorted(set(codes))
        except Exception:
            if attempt >= max_retries - 1:
                return []
            time.sleep(max(sleep_seconds, 0) + 1.0)
    return []


def build_snapshot_payload(
    pro,
    trade_date: str,
    idx_type: Optional[str] = None,
    sleep_seconds: float = 0.2,
) -> Dict:
    """构建板块成分快照数据结构。

    参数：
    - pro: Tushare Pro 客户端对象。
    - trade_date (str): 交易日，格式 YYYYMMDD。
    - idx_type (Optional[str]): 板块类型过滤；为空时导出全部。
    - sleep_seconds (float): 单次 `dc_member` 请求后的休眠秒数。

    返回值：
    - Dict: 可直接写入 JSON 的快照数据。

    异常：
    - 无。单个板块抓取失败时按空成员处理并继续后续板块。
    """
    board_rows = fetch_board_rows(pro, trade_date=trade_date, idx_type=idx_type)
    boards: List[Dict] = []
    for row in board_rows:
        sector_code = normalize_text(row.get("ts_code"))
        if not sector_code:
            continue
        members = fetch_members_for_board(
            pro,
            trade_date=trade_date,
            board_code=sector_code,
            sleep_seconds=sleep_seconds,
        )
        boards.append(
            {
                "sector_code": sector_code,
                "sector_name": normalize_text(row.get("name")),
                "idx_type": normalize_text(row.get("idx_type")),
                "level": normalize_text(row.get("level")),
                "trade_date": normalize_text(row.get("trade_date")),
                "member_count": len(members),
                "members": members,
            }
        )

    return {
        "generated_at": datetime.now().isoformat(),
        "trade_date": trade_date,
        "board_count": len(boards),
        "idx_type_filter": idx_type or "",
        "boards": boards,
    }


def write_snapshot_file(payload: Dict, output_file: Path) -> None:
    """写入板块成分快照 JSON 文件。

    参数：
    - payload (Dict): 快照数据。
    - output_file (Path): 输出文件路径。

    返回值：
    - 无。

    异常：
    - OSError: 文件写入失败时抛出。
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)


def main() -> int:
    """执行快照导出主流程。

    参数：
    - 无。

    返回值：
    - int: 进程退出码，0 表示成功。

    异常：
    - 无。内部异常会被捕获并打印后返回非 0 状态码。
    """
    try:
        args = parse_args()
        ts.set_token(args.token)
        pro = ts.pro_api(args.token)
        latest_trade_date = get_latest_trade_date(pro)
        payload = build_snapshot_payload(
            pro,
            trade_date=latest_trade_date,
            idx_type=(args.idx_type or "").strip() or None,
            sleep_seconds=max(args.sleep_seconds or 0, 0),
        )
        output_file = Path(args.output).resolve()
        write_snapshot_file(payload, output_file)
        print(
            json.dumps(
                {
                    "status": "success",
                    "trade_date": latest_trade_date,
                    "board_count": payload.get("board_count", 0),
                    "output_file": str(output_file),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
