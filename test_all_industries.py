#!/usr/bin/env python3
"""
测试：返回所有行业（包括没有涨停的行业）
"""

import json
from stock_strategy.limit_board_service import limit_board_data_service


def test_all_industries():
    """测试返回所有行业功能"""
    print("=" * 80)
    print("测试：返回所有行业（包括 limit_up_count=0 的行业）")
    print("=" * 80)

    start_date = input("请输入开始日期 (YYYYMMDD，默认 20260701): ").strip() or "20260701"
    end_date = input("请输入结束日期 (YYYYMMDD，默认 20260703): ").strip() or "20260703"

    # 测试1: 使用 default 映射（只返回有涨停的行业）
    print("\n[测试1] default 映射方式 - 只返回有涨停的行业")
    print("-" * 80)
    try:
        result = limit_board_data_service.get_industry_trend_strength(
            start_date=start_date,
            end_date=end_date,
            industry_mapping="default"
        )

        trade_dates = sorted(result['data'].keys())
        if trade_dates:
            first_date = trade_dates[0]
            industries = result['data'][first_date]['industries']

            print(f"交易日: {first_date}")
            print(f"返回的行业数: {len(industries)}")

            # 统计有涨停和没涨停的行业
            with_limit_up = sum(1 for ind in industries if ind['limit_up_count'] > 0)
            without_limit_up = sum(1 for ind in industries if ind['limit_up_count'] == 0)

            print(f"  有涨停的行业: {with_limit_up}")
            print(f"  无涨停的行业: {without_limit_up}")

            if without_limit_up > 0:
                print(f"  ❌ 意外：default 映射应该只返回有涨停的行业")
            else:
                print(f"  ✅ 正确：只返回有涨停的行业")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    # 测试2: 使用东财板块映射（返回所有行业）
    print("\n[测试2] dc_l2 映射方式 - 返回所有行业（包括无涨停的）")
    print("-" * 80)
    try:
        result = limit_board_data_service.get_industry_trend_strength(
            start_date=start_date,
            end_date=end_date,
            industry_mapping="dc_l2"
        )

        trade_dates = sorted(result['data'].keys())
        if trade_dates:
            first_date = trade_dates[0]
            industries = result['data'][first_date]['industries']

            print(f"交易日: {first_date}")
            print(f"返回的行业数: {len(industries)}")

            # 统计有涨停和没涨停的行业
            with_limit_up = sum(1 for ind in industries if ind['limit_up_count'] > 0)
            without_limit_up = sum(1 for ind in industries if ind['limit_up_count'] == 0)

            print(f"  有涨停的行业: {with_limit_up}")
            print(f"  无涨停的行业: {without_limit_up}")

            if without_limit_up > 0:
                print(f"  ✅ 正确：返回了无涨停的行业")
            else:
                print(f"  ⚠️  该交易日所有行业都有涨停股（或 dc_daily 数据缺失）")

            # 显示前5个有涨停的行业
            print(f"\n  前5个有涨停的行业:")
            count = 0
            for ind in industries:
                if ind['limit_up_count'] > 0 and count < 5:
                    pct_change = ind.get('industry_pct_change', 'N/A')
                    print(f"    {count+1}. {ind['industry']}: 涨停{ind['limit_up_count']}只, 涨跌幅{pct_change}%")
                    count += 1

            # 显示前5个无涨停的行业
            print(f"\n  前5个无涨停的行业:")
            count = 0
            for ind in industries:
                if ind['limit_up_count'] == 0 and count < 5:
                    pct_change = ind.get('industry_pct_change', 'N/A')
                    print(f"    {count+1}. {ind['industry']}: 涨停0只, 涨跌幅{pct_change}%")
                    count += 1

            # 检查 industry_pct_change 字段覆盖率
            with_pct_change = sum(1 for ind in industries if 'industry_pct_change' in ind)
            print(f"\n  有 industry_pct_change 字段的行业: {with_pct_change}/{len(industries)} ({with_pct_change/len(industries)*100:.1f}%)")

            if with_pct_change > 0:
                print(f"  ✅ industry_pct_change 字段已返回")
            else:
                print(f"  ❌ 所有行业都缺少 industry_pct_change 字段")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_all_industries()
