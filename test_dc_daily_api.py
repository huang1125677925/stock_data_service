#!/usr/bin/env python3
"""
测试 dc_daily 接口是否可用
"""

from common.tushare_proxy import call_tushare
import json


def test_dc_daily_api():
    """测试 dc_daily 接口"""
    print("=" * 80)
    print("测试 Tushare dc_daily 接口")
    print("=" * 80)

    # 使用最近的真实日期（2024年）
    test_cases = [
        {"start_date": "20240101", "end_date": "20240105", "desc": "2024年1月初"},
        {"start_date": "20240701", "end_date": "20240705", "desc": "2024年7月初"},
    ]

    for case in test_cases:
        print(f"\n测试场景: {case['desc']}")
        print(f"日期范围: {case['start_date']} - {case['end_date']}")
        print("-" * 80)

        try:
            # 调用 dc_daily 接口
            resp = call_tushare(
                "dc_daily",
                params={
                    "start_date": case['start_date'],
                    "end_date": case['end_date']
                },
                fields="trade_date,ts_code,name,pct_change",
                use_query=False
            )

            print(f"响应代码: {resp.get('code')}")
            print(f"响应消息: {resp.get('message', 'N/A')}")

            if resp.get('code') == 200:
                data = resp.get('data') or {}
                records = data.get('records') or []
                print(f"✅ 接口调用成功，返回 {len(records)} 条记录")

                if records:
                    # 显示前3条记录
                    print(f"\n前3条记录示例:")
                    for i, record in enumerate(records[:3], 1):
                        print(f"  {i}. 日期: {record.get('trade_date')}, "
                              f"代码: {record.get('ts_code')}, "
                              f"名称: {record.get('name')}, "
                              f"涨跌幅: {record.get('pct_change')}%")
                else:
                    print("⚠️  接口返回成功但没有数据")
                    print("   可能是该日期范围确实没有板块行情")

            else:
                print(f"❌ 接口调用失败")
                print(f"   错误信息: {resp.get('message')}")
                print(f"   可能原因:")
                print(f"   1. Tushare 账号没有 dc_daily 接口权限")
                print(f"   2. 积分不足")
                print(f"   3. 接口调用频率超限")

        except Exception as e:
            print(f"❌ 异常: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

    print("\n建议:")
    print("1. 如果所有测试都返回 0 条记录，请检查 Tushare 账号权限")
    print("2. 登录 https://tushare.pro/ 查看接口权限")
    print("3. dc_daily 接口可能需要特定的积分或权限等级")
    print("4. 可以尝试直接在 Tushare 网站测试该接口")


if __name__ == "__main__":
    test_dc_daily_api()
