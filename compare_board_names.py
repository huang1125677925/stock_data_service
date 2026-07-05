#!/usr/bin/env python3
"""
比对 dc_daily 返回的板块名称和快照中的板块名称
"""

import json
from common.tushare_proxy import call_tushare
from pathlib import Path


def compare_board_names():
    """比对板块名称"""
    print("=" * 80)
    print("比对 dc_daily 板块名称和快照板块名称")
    print("=" * 80)

    # 1. 获取 dc_daily 的板块名称
    print("\n[步骤1] 获取 dc_daily 板块名称...")
    resp = call_tushare(
        "dc_daily",
        params={
            "start_date": "20260701",
            "end_date": "20260701"
        },
        fields="trade_date,ts_code,name",
        use_query=False
    )

    dc_daily_boards = {}
    if resp.get('code') == 200:
        records = resp.get('data', {}).get('records', [])
        print(f"  获取到 {len(records)} 条板块记录")

        for record in records:
            ts_code = record.get('ts_code', '')
            name = record.get('name', '')
            if ts_code and name:
                dc_daily_boards[name] = ts_code

        print(f"  去重后有 {len(dc_daily_boards)} 个不同的板块")
        print(f"\n  dc_daily 板块名称示例（前20个）:")
        for i, name in enumerate(list(dc_daily_boards.keys())[:20], 1):
            print(f"    {i}. {name} ({dc_daily_boards[name]})")
    else:
        print(f"  ❌ 获取失败: {resp.get('message')}")
        return

    # 2. 读取快照中的板块名称
    print("\n[步骤2] 读取快照中的板块名称...")
    snapshot_file = Path(__file__).resolve().parent / "data" / "dc_board_members_snapshot.json"

    if not snapshot_file.exists():
        print(f"  ❌ 快照文件不存在: {snapshot_file}")
        return

    with open(snapshot_file, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    # 筛选东财二级行业
    dc_l2_boards = {}
    for board in snapshot:
        if board.get('idx_type') == '行业板块' and board.get('level') == '东财二级行业':
            sector_name = board.get('sector_name', '')
            sector_code = board.get('sector_code', '')
            if sector_name:
                dc_l2_boards[sector_name] = sector_code

    print(f"  快照中有 {len(dc_l2_boards)} 个东财二级行业板块")
    print(f"\n  快照板块名称示例（前20个）:")
    for i, name in enumerate(list(dc_l2_boards.keys())[:20], 1):
        print(f"    {i}. {name} ({dc_l2_boards.get(name, 'N/A')})")

    # 3. 比对名称
    print("\n[步骤3] 比对板块名称...")

    # 快照中的名称在 dc_daily 中能找到的
    matched_names = set(dc_l2_boards.keys()) & set(dc_daily_boards.keys())
    print(f"  完全匹配的板块: {len(matched_names)} 个")

    if matched_names:
        print(f"\n  匹配的板块示例（前10个）:")
        for i, name in enumerate(list(matched_names)[:10], 1):
            print(f"    {i}. {name}")

    # 快照中的名称在 dc_daily 中找不到的
    snapshot_only = set(dc_l2_boards.keys()) - set(dc_daily_boards.keys())
    print(f"\n  仅在快照中的板块: {len(snapshot_only)} 个")

    if snapshot_only:
        print(f"\n  仅在快照中的板块示例（前10个）:")
        for i, name in enumerate(list(snapshot_only)[:10], 1):
            print(f"    {i}. {name}")

    # dc_daily 中的名称在快照中找不到的
    dc_daily_only = set(dc_daily_boards.keys()) - set(dc_l2_boards.keys())
    print(f"\n  仅在 dc_daily 中的板块: {len(dc_daily_only)} 个")

    if dc_daily_only:
        print(f"\n  仅在 dc_daily 中的板块示例（前10个）:")
        for i, name in enumerate(list(dc_daily_only)[:10], 1):
            print(f"    {i}. {name}")

    # 4. 尝试通过板块代码匹配
    print("\n[步骤4] 尝试通过板块代码匹配...")

    # 构建代码到名称的映射
    dc_daily_code_to_name = {code: name for name, code in dc_daily_boards.items()}
    snapshot_code_to_name = {code: name for name, code in dc_l2_boards.items()}

    # 找出代码相同但名称不同的
    code_matched_diff_name = []
    for code in set(dc_daily_code_to_name.keys()) & set(snapshot_code_to_name.keys()):
        dc_name = dc_daily_code_to_name[code]
        snapshot_name = snapshot_code_to_name[code]
        if dc_name != snapshot_name:
            code_matched_diff_name.append((code, snapshot_name, dc_name))

    if code_matched_diff_name:
        print(f"  发现 {len(code_matched_diff_name)} 个板块代码相同但名称不同:")
        print(f"\n  板块代码 | 快照名称 | dc_daily名称")
        print(f"  " + "-" * 70)
        for code, snap_name, dc_name in code_matched_diff_name[:20]:
            print(f"  {code} | {snap_name} | {dc_name}")
    else:
        print(f"  没有发现代码相同但名称不同的板块")

    # 5. 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print(f"完全匹配率: {len(matched_names)}/{len(dc_l2_boards)} = {len(matched_names)/len(dc_l2_boards)*100:.1f}%")

    if len(matched_names) < len(dc_l2_boards) * 0.5:
        print("\n⚠️  匹配率低于50%，建议使用板块代码匹配而非板块名称")
    elif code_matched_diff_name:
        print("\n⚠️  存在代码相同但名称不同的板块，建议优先使用板块代码匹配")
    else:
        print("\n✅ 名称匹配情况良好")


if __name__ == "__main__":
    compare_board_names()
