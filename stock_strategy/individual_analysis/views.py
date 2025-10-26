import json
import numpy as np
import pandas as pd
import talib
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from common.response import success_response, error_response
from indival_stock_data.models import IndividualStock, IndividualStockDaily

# 由于项目中未引入TA-Lib，这里实现部分常见K线形态识别的简化版本逻辑。
# 若后续引入TA-Lib，可将具体形态识别函数替换为talib对应函数的输出。


def _build_ohlc_dataframe(daily_qs):
    """
    构建包含日期、开盘、最高、最低、收盘列的DataFrame
    参数：
        daily_qs: QuerySet[IndividualStockDaily]，数据库查询结果
    返回：
        DataFrame，列包含：日期、开盘、最高、最低、收盘
    """
    rows = []
    for d in daily_qs:
        rows.append({
            '日期': d.date,
            '开盘': float(d.open_price),
            '最高': float(d.high_price),
            '最低': float(d.low_price),
            '收盘': float(d.close_price)
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values('日期').reset_index(drop=True)
    return df


def recognize_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    识别股票的K线形态

    功能：
        使用TA-Lib识别多种常见的K线形态，并返回逐日的形态信号值。
    参数:
        df: DataFrame, 包含日期("日期"), 开盘("开盘"), 最高("最高"), 最低("最低"), 收盘("收盘")等列
    返回:
        包含所有识别形态的DataFrame（各列为形态信号，+100为看涨信号，-100为看跌信号，0为无信号）
    事件：
        - 不进行外部数据获取，严格依据数据库已有数据进行识别
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['日期'])

    # 确保数据按日期升序排列（TA-Lib要求）
    df = df.sort_values('日期').reset_index(drop=True)

    # 提取OHLC数据并转换为numpy数组（TA-Lib要求的格式）
    open_prices = np.array(df['开盘'], dtype=float)
    high_prices = np.array(df['最高'], dtype=float)
    low_prices = np.array(df['最低'], dtype=float)
    close_prices = np.array(df['收盘'], dtype=float)

    # 初始化结果字典
    patterns = {
        '日期': df['日期'].values
    }

    # 识别各种K线形态
    # 看涨形态（函数返回+100表示看涨信号）
    patterns['锤子线'] = talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices)
    patterns['早晨之星'] = talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['看涨刺透'] = talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices)
    patterns['看涨反击线'] = talib.CDLKICKING(open_prices, high_prices, low_prices, close_prices)
    patterns['倒锤头'] = talib.CDLINVERTEDHAMMER(open_prices, high_prices, low_prices, close_prices)

    # 注意：ENGULFING和HARAMI通过返回值区分看涨看跌
    # 返回+100为看涨吞没，-100为看跌吞没
    patterns['吞没形态'] = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices)
    patterns['孕线'] = talib.CDLHARAMI(open_prices, high_prices, low_prices, close_prices)

    # 看跌形态（函数返回-100表示看跌信号）
    patterns['上吊线'] = talib.CDLHANGINGMAN(open_prices, high_prices, low_prices, close_prices)
    patterns['黄昏之星'] = talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['乌云盖顶'] = talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices)
    patterns['三只乌鸦'] = talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices)  # 修正后的正确函数名
    patterns['三胞胎乌鸦'] = talib.CDLIDENTICAL3CROWS(open_prices, high_prices, low_prices, close_prices)  # 另一个乌鸦形态

    # 中性/特殊形态
    patterns['十字星'] = talib.CDLDOJI(open_prices, high_prices, low_prices, close_prices)
    patterns['长腿十字星'] = talib.CDLLONGLEGGEDDOJI(open_prices, high_prices, low_prices, close_prices)
    patterns['墓碑十字星'] = talib.CDLGRAVESTONEDOJI(open_prices, high_prices, low_prices, close_prices)

    # 其他TA-Lib形态（完整补充）
    patterns['两只乌鸦'] = talib.CDL2CROWS(open_prices, high_prices, low_prices, close_prices)
    patterns['三内部上涨/下跌'] = talib.CDL3INSIDE(open_prices, high_prices, low_prices, close_prices)
    patterns['三线打击'] = talib.CDL3LINESTRIKE(open_prices, high_prices, low_prices, close_prices)
    patterns['三外部上涨/下跌'] = talib.CDL3OUTSIDE(open_prices, high_prices, low_prices, close_prices)
    patterns['南方三星'] = talib.CDL3STARSINSOUTH(open_prices, high_prices, low_prices, close_prices)
    patterns['三个白兵'] = talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices)
    patterns['弃婴'] = talib.CDLABANDONEDBABY(open_prices, high_prices, low_prices, close_prices)
    patterns['大敌当前'] = talib.CDLADVANCEBLOCK(open_prices, high_prices, low_prices, close_prices)
    patterns['捉腰带线'] = talib.CDLBELTHOLD(open_prices, high_prices, low_prices, close_prices)
    patterns['脱离形态'] = talib.CDLBREAKAWAY(open_prices, high_prices, low_prices, close_prices)
    patterns['收盘秃线'] = talib.CDLCLOSINGMARUBOZU(open_prices, high_prices, low_prices, close_prices)
    patterns['藏婴吞没'] = talib.CDLCONCEALBABYSWALL(open_prices, high_prices, low_prices, close_prices)
    patterns['反击线'] = talib.CDLCOUNTERATTACK(open_prices, high_prices, low_prices, close_prices)
    patterns['十字星形态'] = talib.CDLDOJISTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['蜻蜓十字'] = talib.CDLDRAGONFLYDOJI(open_prices, high_prices, low_prices, close_prices)
    patterns['十字暮星'] = talib.CDLEVENINGDOJISTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['并列阳线'] = talib.CDLGAPSIDESIDEWHITE(open_prices, high_prices, low_prices, close_prices)
    patterns['家鸽'] = talib.CDLHOMINGPIGEON(open_prices, high_prices, low_prices, close_prices)
    patterns['颈内线'] = talib.CDLINNECK(open_prices, high_prices, low_prices, close_prices)
    patterns['由较长秃线决定的反冲'] = talib.CDLKICKINGBYLENGTH(open_prices, high_prices, low_prices, close_prices)
    patterns['梯底'] = talib.CDLLADDERBOTTOM(open_prices, high_prices, low_prices, close_prices)
    patterns['长线'] = talib.CDLLONGLINE(open_prices, high_prices, low_prices, close_prices)
    patterns['秃线'] = talib.CDLMARUBOZU(open_prices, high_prices, low_prices, close_prices)
    patterns['相同低价'] = talib.CDLMATCHINGLOW(open_prices, high_prices, low_prices, close_prices)
    patterns['垫脚石'] = talib.CDLMATHOLD(open_prices, high_prices, low_prices, close_prices)
    patterns['十字晨星'] = talib.CDLMORNINGDOJISTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['颈上线'] = talib.CDLONNECK(open_prices, high_prices, low_prices, close_prices)
    patterns['黄包车夫'] = talib.CDLRICKSHAWMAN(open_prices, high_prices, low_prices, close_prices)
    patterns['上升/下降三法'] = talib.CDLRISEFALL3METHODS(open_prices, high_prices, low_prices, close_prices)
    patterns['分离线'] = talib.CDLSEPARATINGLINES(open_prices, high_prices, low_prices, close_prices)
    patterns['射击之星'] = talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['短线'] = talib.CDLSHORTLINE(open_prices, high_prices, low_prices, close_prices)
    patterns['纺锤线'] = talib.CDLSPINNINGTOP(open_prices, high_prices, low_prices, close_prices)
    patterns['停顿形态'] = talib.CDLSTALLEDPATTERN(open_prices, high_prices, low_prices, close_prices)
    patterns['条形三明治'] = talib.CDLSTICKSANDWICH(open_prices, high_prices, low_prices, close_prices)
    patterns['探水杆'] = talib.CDLTAKURI(open_prices, high_prices, low_prices, close_prices)
    patterns['跳空并列线'] = talib.CDLTASUKIGAP(open_prices, high_prices, low_prices, close_prices)
    patterns['插入形态'] = talib.CDLTHRUSTING(open_prices, high_prices, low_prices, close_prices)
    patterns['三星'] = talib.CDLTRISTAR(open_prices, high_prices, low_prices, close_prices)
    patterns['独特三河'] = talib.CDLUNIQUE3RIVER(open_prices, high_prices, low_prices, close_prices)
    patterns['向上跳空两只乌鸦'] = talib.CDLUPSIDEGAP2CROWS(open_prices, high_prices, low_prices, close_prices)
    patterns['向上/向下跳空三法'] = talib.CDLXSIDEGAP3METHODS(open_prices, high_prices, low_prices, close_prices)

    # 创建结果DataFrame
    result_df = pd.DataFrame(patterns)
    return result_df


@csrf_exempt
@require_http_methods(["GET"])
def analyze_candlestick_patterns(request, stock_code: str):
    """
    分析个股股票K线形态接口

    功能：
        基于数据库中个股日频数据，识别指定股票的常见K线形态，返回逐日的形态信号值。
    参数：
        stock_code (str): 路径参数，股票代码。
        start_date (str): 查询开始日期（YYYY-MM-DD），可选。
        end_date (str): 查询结束日期（YYYY-MM-DD），可选。
    返回值：
        - 成功：标准success_response，data包含：
            {
                'stock_code': str,
                'stock_name': str,
                'total': int,
                'patterns': [
                    {
                        'date': 'YYYY-MM-DD',
                        'hammer': int,
                        'morning_star': int,
                        'piercing': int,
                        'kicking': int,
                        'inverted_hammer': int,
                        'engulfing': int,
                        'harami': int,
                        'hanging_man': int,
                        'evening_star': int,
                        'dark_cloud_cover': int,
                        'three_black_crows': int,
                        'identical_three_crows': int,
                        'doji': int,
                        'long_legged_doji': int,
                        'gravestone_doji': int
                    }, ...
                ]
            }
        - 失败：标准error_response，包含错误说明。
    事件：
        - 数据查询与识别过程中不调用外部接口。
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # 验证股票存在
        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        # 从数据库获取日频数据
        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')

        if not qs.exists():
            return error_response('无日频数据', 404)

        df = _build_ohlc_dataframe(qs)
        patterns_df = recognize_candlestick_patterns(df)

        # 构建输出
        output = []
        for _, row in patterns_df.iterrows():
            output.append({
                'date': pd.to_datetime(row['日期']).date().isoformat(),
                'hammer': int(row['锤子线']),
                'morning_star': int(row['早晨之星']),
                'piercing': int(row['看涨刺透']),
                'kicking': int(row['看涨反击线']),
                'inverted_hammer': int(row['倒锤头']),
                'engulfing': int(row['吞没形态']),
                'harami': int(row['孕线']),
                'hanging_man': int(row['上吊线']),
                'evening_star': int(row['黄昏之星']),
                'dark_cloud_cover': int(row['乌云盖顶']),
                'three_black_crows': int(row['三只乌鸦']),
                'identical_three_crows': int(row['三胞胎乌鸦']),
                'doji': int(row['十字星']),
                'long_legged_doji': int(row['长腿十字星']),
                'gravestone_doji': int(row['墓碑十字星']),
                # 新增返回字段
                'two_crows': int(row['两只乌鸦']),
                'three_inside': int(row['三内部上涨/下跌']),
                'three_line_strike': int(row['三线打击']),
                'three_outside': int(row['三外部上涨/下跌']),
                'three_stars_in_south': int(row['南方三星']),
                'three_white_soldiers': int(row['三个白兵']),
                'abandoned_baby': int(row['弃婴']),
                'advance_block': int(row['大敌当前']),
                'belt_hold': int(row['捉腰带线']),
                'breakaway': int(row['脱离形态']),
                'closing_marubozu': int(row['收盘秃线']),
                'conceal_baby_swallow': int(row['藏婴吞没']),
                'counterattack': int(row['反击线']),
                'doji_star': int(row['十字星形态']),
                'dragonfly_doji': int(row['蜻蜓十字']),
                'evening_doji_star': int(row['十字暮星']),
                'gap_side_by_side_white': int(row['并列阳线']),
                'homing_pigeon': int(row['家鸽']),
                'in_neck': int(row['颈内线']),
                'kicking_by_length': int(row['由较长秃线决定的反冲']),
                'ladder_bottom': int(row['梯底']),
                'long_line': int(row['长线']),
                'marubozu': int(row['秃线']),
                'matching_low': int(row['相同低价']),
                'mat_hold': int(row['垫脚石']),
                'morning_doji_star': int(row['十字晨星']),
                'on_neck': int(row['颈上线']),
                'rickshaw_man': int(row['黄包车夫']),
                'rise_fall_three_methods': int(row['上升/下降三法']),
                'separating_lines': int(row['分离线']),
                'shooting_star': int(row['射击之星']),
                'short_line': int(row['短线']),
                'spinning_top': int(row['纺锤线']),
                'stalled_pattern': int(row['停顿形态']),
                'stick_sandwich': int(row['条形三明治']),
                'takuri': int(row['探水杆']),
                'tasuki_gap': int(row['跳空并列线']),
                'thrusting': int(row['插入形态']),
                'tristar': int(row['三星']),
                'unique_three_river': int(row['独特三河']),
                'upside_gap_two_crows': int(row['向上跳空两只乌鸦']),
                'xside_gap_three_methods': int(row['向上/向下跳空三法']),
            })

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'total': len(output),
            'patterns': output,
        }

        return success_response(data, '识别K线形态成功')

    except Exception as e:
        return error_response(f'识别K线形态失败: {str(e)}', 500)