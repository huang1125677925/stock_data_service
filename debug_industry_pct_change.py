#!/usr/bin/env python3
"""
调试脚本：检查 industry_pct_change 字段为何没有返回
"""

import json
from stock_strategy.limit_board_service import limit_board_data_service


def debug_industry_pct_change():
    """调试 industry_pct_change 字段"""
    print("=" * 80)
    print("调试：industry_pct_change 字段缺失问题")
    print("=" * 80)

    # 使用你实际请求的参数
    start_date = input("请输入开始日期 (YYYYMMDD): ").strip() or "20260101"
    end_date = input("请输入结束日期 (YYYYMMDD): ").strip() or "20260110"
    industry_mapping = input("请输入行业映射方式 (默认 dc_l2): ").strip() or "dc_l2"

    print(f"\n查询参数:")
    print(f"  start_date: {start_date}")
    print(f"  end_date: {end_date}")
    print(f"  industry_mapping: {industry_mapping}")
    print("\n" + "-" * 80)

    try:
        result = limit_board_data_service.get_industry_trend_strength(
            start_date=start_date,
            end_date=end_date,
            industry_mapping=industry_mapping,
        )

        print(f"\n✅ 接口调用成功")
        print(f"\n数据源统计:")
        print(json.dumps(result['source_counts'], indent=2, ensure_ascii=False))

        # 检查是否使用了板块映射
        is_snapshot = industry_mapping != "default"
        print(f"\n是否使用板块映射: {is_snapshot}")
        print(f"板块映射方式: {result['summary']['industry_mapping']}")

        # 检查 dc_daily 数据量
        dc_daily_count = result['source_counts'].get('dc_daily', 0)
        print(f"dc_daily 记录数: {dc_daily_count}")

        if dc_daily_count == 0:
            print("\n⚠️  警告: dc_daily 接口返回 0 条记录")
            print("   可能原因：")
            print("   1. 查询的日期范围没有板块行情数据")
            print("   2. Tushare 接口权限不足")
            print("   3. 日期格式问题")

        # 检查交易日数据
        trade_dates = sorted(result['data'].keys())
        print(f"\n有数据的交易日数: {len(trade_dates)}")

        if trade_dates:
            print(f"交易日列表: {trade_dates}")

            # 检查第一个交易日的行业数据
            first_date = trade_dates[0]
            print(f"\n检查第一个交易日 {first_date} 的行业数据:")

            industries = result['data'][first_date]['industries']
            print(f"  行业数量: {len(industries)}")

            if industries:
                # 显示前3个行业的详细信息
                for i, industry in enumerate(industries[:3], 1):
                    print(f"\n  行业 {i}: {industry['industry']}")
                    print(f"    涨停数: {industry['limit_up_count']}")

                    # 检查是否有 industry_pct_change 字段
                    if 'industry_pct_change' in industry:
                        print(f"    ✅ 行业涨跌幅: {industry['industry_pct_change']}%")
                    else:
                        print(f"    ❌ 缺少 industry_pct_change 字段")
                        print(f"    行业字段: {list(industry.keys())}")

                # 统计有多少行业有 industry_pct_change 字段
                with_pct_change = sum(1 for ind in industries if 'industry_pct_change' in ind)
                print(f"\n  总结: {with_pct_change}/{len(industries)} 个行业有 industry_pct_change 字段")

                if with_pct_change == 0:
                    print("\n  ⚠️  所有行业都缺少 industry_pct_change 字段")
                    print("  可能原因：")
                    print("  1. dc_daily 板块名称与快照中的板块名称不匹配")
                    print("  2. dc_daily 数据中没有这些行业的记录")

                    # 显示行业名称列表
                    industry_names = [ind['industry'] for ind in industries[:10]]
                    print(f"\n  前10个行业名称:")
                    for name in industry_names:
                        print(f"    - {name}")

            else:
                print("  ❌ 没有行业数据")

        else:
            print("\n⚠️  警告: 查询区间内没有交易日数据")
            print("   请检查日期范围是否正确，或该区间是否有涨停股数据")

    except Exception as e:
        print(f"\n❌ 接口调用失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)


if __name__ == "__main__":
    debug_industry_pct_change()
