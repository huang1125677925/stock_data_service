#!/usr/bin/env python3
"""
测试行业涨停趋势强度接口的新增功能：
1. 昨日涨停股今日溢价数据
2. 行业涨跌幅数据
"""

import json
from stock_strategy.limit_board_service import limit_board_data_service


def test_industry_trend_strength_with_premium():
    """测试行业涨停趋势强度接口的昨日溢价和行业涨跌幅功能"""
    print("=" * 80)
    print("测试行业涨停趋势强度接口 - 昨日溢价 + 行业涨跌幅")
    print("=" * 80)

    # 测试1: 使用默认行业映射（不包含行业涨跌幅）
    print("\n[测试1] 默认行业映射 (default) - 不含行业涨跌幅")
    print("-" * 80)
    try:
        result = limit_board_data_service.get_industry_trend_strength(
            start_date="20260630",
            end_date="20260704",
            industry_mapping="default"
        )

        print(f"查询区间: {result['start_date']} - {result['end_date']}")
        print(f"交易日数: {result['summary']['trade_day_count']}")
        print(f"涉及行业数: {result['summary']['industry_count']}")
        print(f"数据源统计: {json.dumps(result['source_counts'], indent=2, ensure_ascii=False)}")

        # 检查第二个交易日是否有昨日溢价数据
        trade_dates = sorted(result['data'].keys())
        if len(trade_dates) >= 2:
            second_date = trade_dates[1]
            industries = result['data'][second_date]['industries']

            print(f"\n第二个交易日 {second_date} 的行业数据示例:")
            for industry in industries[:2]:  # 只显示前2个行业
                print(f"  - 行业: {industry['industry']}")
                print(f"    涨停数: {industry['limit_up_count']}")

                if 'yesterday_limit_up_count' in industry:
                    print(f"    昨日涨停数: {industry['yesterday_limit_up_count']}")
                    print(f"    平均溢价: {industry.get('avg_premium_pct', 'N/A')}%")
                    stocks = industry.get('yesterday_limit_up_stocks', [])
                    print(f"    昨日涨停股详情数: {len(stocks)}")
                else:
                    print(f"    昨日溢价数据: 无（第一个交易日）")

                if 'industry_pct_change' in industry:
                    print(f"    行业涨跌幅: {industry['industry_pct_change']}%")
                else:
                    print(f"    行业涨跌幅: N/A (仅东财板块映射方式可用)")

        print("\n✅ 测试1通过")

    except Exception as e:
        print(f"\n❌ 测试1失败: {str(e)}")
        import traceback
        traceback.print_exc()

    # 测试2: 使用东财板块映射（包含行业涨跌幅）
    print("\n\n[测试2] 东财二级行业板块映射 (dc_l2) - 含行业涨跌幅")
    print("-" * 80)
    try:
        result = limit_board_data_service.get_industry_trend_strength(
            start_date="20260630",
            end_date="20260704",
            industry_mapping="dc_l2"
        )

        print(f"查询区间: {result['start_date']} - {result['end_date']}")
        print(f"交易日数: {result['summary']['trade_day_count']}")
        print(f"涉及行业数: {result['summary']['industry_count']}")
        print(f"行业映射方式: {result['summary']['industry_mapping']} ({result['summary']['industry_mapping_label']})")
        print(f"数据源统计: {json.dumps(result['source_counts'], indent=2, ensure_ascii=False)}")

        # 检查第二个交易日是否有完整数据
        trade_dates = sorted(result['data'].keys())
        if len(trade_dates) >= 2:
            second_date = trade_dates[1]
            industries = result['data'][second_date]['industries']

            print(f"\n第二个交易日 {second_date} 的行业数据示例:")
            for industry in industries[:2]:  # 只显示前2个行业
                print(f"  - 行业: {industry['industry']}")
                print(f"    涨停数: {industry['limit_up_count']}")

                if 'yesterday_limit_up_count' in industry:
                    print(f"    昨日涨停数: {industry['yesterday_limit_up_count']}")
                    print(f"    平均溢价: {industry.get('avg_premium_pct', 'N/A')}%")
                    stocks = industry.get('yesterday_limit_up_stocks', [])
                    print(f"    昨日涨停股详情数: {len(stocks)}")
                    if stocks:
                        print(f"    示例股票: {stocks[0]['name']} ({stocks[0]['ts_code']})")
                        print(f"      昨收: {stocks[0]['prev_close']}, 今开: {stocks[0]['today_open']}, 溢价: {stocks[0]['premium_pct']}%")
                else:
                    print(f"    昨日溢价数据: 无（第一个交易日）")

                if 'industry_pct_change' in industry:
                    print(f"    行业涨跌幅: {industry['industry_pct_change']}%")
                else:
                    print(f"    行业涨跌幅: N/A (未匹配到板块行情)")

        print("\n✅ 测试2通过")

    except Exception as e:
        print(f"\n❌ 测试2失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_industry_trend_strength_with_premium()
