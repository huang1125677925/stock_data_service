#!/usr/bin/env python3
"""
检查 dc_daily 接口实际返回的字段
"""

from common.tushare_proxy import call_tushare
import json


def check_dc_daily_fields():
    """检查 dc_daily 接口返回的字段"""
    print("=" * 80)
    print("检查 dc_daily 接口返回的字段")
    print("=" * 80)

    print("\n正在调用 dc_daily 接口...")
    resp = call_tushare(
        "dc_daily",
        params={
            "start_date": "20260701",
            "end_date": "20260701"
        },
        fields="trade_date,ts_code,name,pct_change",
        use_query=False
    )

    if resp.get('code') == 200:
        records = resp.get('data', {}).get('records', [])
        print(f"✅ 接口调用成功，返回 {len(records)} 条记录")

        if records:
            print(f"\n第一条记录的所有字段:")
            first_record = records[0]
            print(json.dumps(first_record, indent=2, ensure_ascii=False))

            print(f"\n字段列表:")
            for key in first_record.keys():
                print(f"  - {key}: {first_record[key]}")

            print(f"\n前5条记录:")
            for i, record in enumerate(records[:5], 1):
                print(f"  {i}. ts_code={record.get('ts_code')}, "
                      f"name={record.get('name')}, "
                      f"pct_change={record.get('pct_change')}")
        else:
            print("⚠️  接口返回成功但没有数据")
    else:
        print(f"❌ 接口调用失败: {resp.get('message')}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_dc_daily_fields()
