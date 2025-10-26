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


# ========= 指标计算辅助工具函数 =========

def _build_ohlcv_arrays(daily_qs):
    """
    从个股日频QuerySet构建OHLCV数组与日期序列
    返回: (open, high, low, close, volume, dates)
    """
    dates = []
    open_arr, high_arr, low_arr, close_arr, volume_arr = [], [], [], [], []
    for d in daily_qs:
        dates.append(d.date)
        open_arr.append(float(d.open_price))
        high_arr.append(float(d.high_price))
        low_arr.append(float(d.low_price))
        close_arr.append(float(d.close_price))
        # volume 可能为None，统一转float
        volume_arr.append(float(d.volume or 0))
    return (
        np.array(open_arr, dtype=float),
        np.array(high_arr, dtype=float),
        np.array(low_arr, dtype=float),
        np.array(close_arr, dtype=float),
        np.array(volume_arr, dtype=float),
        dates,
    )


def _nan_to_none(x):
    try:
        if x is None:
            return None
        return None if (isinstance(x, float) and np.isnan(x)) else float(x)
    except Exception:
        return None


def _build_output(dates, series_dict):
    """
    将多个指标序列打包为逐日输出列表
    series_dict: { field_name: numpy.ndarray }
    返回: [ { 'date': 'YYYY-MM-DD', field_name: value, ... }, ... ]
    """
    n = len(dates)
    outputs = []
    for i in range(n):
        row = {
            'date': pd.to_datetime(dates[i]).date().isoformat()
        }
        for k, arr in series_dict.items():
            try:
                val = arr[i]
            except Exception:
                val = None
            row[k] = _nan_to_none(val)
        outputs.append(row)
    return outputs


# ========= 分类指标API：重叠研究 =========
@csrf_exempt
@require_http_methods(["GET"])
def analyze_overlap_indicators(request, stock_code: str):
    """
    重叠研究(均线/布林等)指标计算接口
    返回该类别下所有可计算指标的结果
    支持: BBANDS, SMA, EMA, MA, KAMA, T3, TEMA, TRIMA, WMA, DEMA,
          MAMA, MAVP(需periods), MIDPOINT, MIDPRICE, SAR, SAREXT, HT_TRENDLINE
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')
        if not qs.exists():
            return error_response('无日频数据', 404)

        open_p, high_p, low_p, close_p, volume_p, dates = _build_ohlcv_arrays(qs)

        # 通用参数
        timeperiod = int(request.GET.get('timeperiod', 20))
        matype = int(request.GET.get('matype', 0))
        nbdevup = float(request.GET.get('nbdevup', 2))
        nbdevdn = float(request.GET.get('nbdevdn', 2))

        results = {}
        skipped = []

        # BBANDS
        try:
            upper, middle, lower = talib.BBANDS(close_p, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=matype)
            results['BBANDS'] = _build_output(dates, {
                'upperband': upper,
                'middleband': middle,
                'lowerband': lower,
            })
        except Exception as e:
            skipped.append({'indicator': 'BBANDS', 'reason': str(e)})

        # 均线类
        for name in ('SMA', 'EMA', 'DEMA', 'KAMA', 'T3', 'TEMA', 'TRIMA', 'WMA'):
            try:
                func = getattr(talib, name)
                arr = func(close_p, timeperiod=timeperiod)
                results[name] = _build_output(dates, {name.lower(): arr})
            except Exception as e:
                skipped.append({'indicator': name, 'reason': str(e)})
        # MA 允许 matype
        try:
            arr = talib.MA(close_p, timeperiod=timeperiod, matype=matype)
            results['MA'] = _build_output(dates, {'ma': arr})
        except Exception as e:
            skipped.append({'indicator': 'MA', 'reason': str(e)})

        # MAMA
        try:
            fastlimit = float(request.GET.get('fastlimit', 0.5))
            slowlimit = float(request.GET.get('slowlimit', 0.05))
            mama, fama = talib.MAMA(close_p, fastlimit=fastlimit, slowlimit=slowlimit)
            results['MAMA'] = _build_output(dates, {'mama': mama, 'fama': fama})
        except Exception as e:
            skipped.append({'indicator': 'MAMA', 'reason': str(e)})

        # MAVP 需要 periods 序列
        periods_str = request.GET.get('periods')
        if periods_str:
            try:
                periods = np.array([int(x) for x in periods_str.split(',') if x.strip()])
                minperiod = int(request.GET.get('minperiod', 2))
                maxperiod = int(request.GET.get('maxperiod', 30))
                arr = talib.MAVP(close_p, periods, minperiod=minperiod, maxperiod=maxperiod, matype=matype)
                results['MAVP'] = _build_output(dates, {'mavp': arr})
            except Exception as e:
                skipped.append({'indicator': 'MAVP', 'reason': str(e)})
        else:
            skipped.append({'indicator': 'MAVP', 'reason': '缺少 periods 参数'})

        # MIDPOINT
        try:
            arr = talib.MIDPOINT(close_p, timeperiod=timeperiod)
            results['MIDPOINT'] = _build_output(dates, {'midpoint': arr})
        except Exception as e:
            skipped.append({'indicator': 'MIDPOINT', 'reason': str(e)})
        # MIDPRICE
        try:
            arr = talib.MIDPRICE(high_p, low_p, timeperiod=timeperiod)
            results['MIDPRICE'] = _build_output(dates, {'midprice': arr})
        except Exception as e:
            skipped.append({'indicator': 'MIDPRICE', 'reason': str(e)})

        # SAR
        try:
            acceleration = float(request.GET.get('acceleration', 0.02))
            maximum = float(request.GET.get('maximum', 0.2))
            arr = talib.SAR(high_p, low_p, acceleration=acceleration, maximum=maximum)
            results['SAR'] = _build_output(dates, {'sar': arr})
        except Exception as e:
            skipped.append({'indicator': 'SAR', 'reason': str(e)})
        # SAREXT
        try:
            startvalue = float(request.GET.get('startvalue', 0))
            offsetonreverse = float(request.GET.get('offsetonreverse', 0))
            accelerationinitlong = float(request.GET.get('accelerationinitlong', 0))
            accelerationlong = float(request.GET.get('accelerationlong', 0.02))
            accelerationmaxlong = float(request.GET.get('accelerationmaxlong', 0.2))
            accelerationinitshort = float(request.GET.get('accelerationinitshort', 0))
            accelerationshort = float(request.GET.get('accelerationshort', 0.02))
            accelerationmaxshort = float(request.GET.get('accelerationmaxshort', 0.2))
            arr = talib.SAREXT(
                high_p, low_p,
                startvalue=startvalue,
                offsetonreverse=offsetonreverse,
                accelerationinitlong=accelerationinitlong,
                accelerationlong=accelerationlong,
                accelerationmaxlong=accelerationmaxlong,
                accelerationinitshort=accelerationinitshort,
                accelerationshort=accelerationshort,
                accelerationmaxshort=accelerationmaxshort,
            )
            results['SAREXT'] = _build_output(dates, {'sarext': arr})
        except Exception as e:
            skipped.append({'indicator': 'SAREXT', 'reason': str(e)})

        # HT_TRENDLINE
        try:
            arr = talib.HT_TRENDLINE(close_p)
            results['HT_TRENDLINE'] = _build_output(dates, {'ht_trendline': arr})
        except Exception as e:
            skipped.append({'indicator': 'HT_TRENDLINE', 'reason': str(e)})

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'category': 'overlap',
            'indicators': results,
            'skipped': skipped,
            'total': len(dates)
        }
        return success_response(data, '计算重叠研究指标成功')
    except Exception as e:
        return error_response(f'计算重叠研究指标失败: {str(e)}', 500)


# ========= 分类指标API：动量指标 =========
@csrf_exempt
@require_http_methods(["GET"])
def analyze_momentum_indicators(request, stock_code: str):
    """
    动量类指标计算接口
    返回该类别下所有可计算指标的结果
    支持: ADX, ADXR, APO, AROON, AROONOSC, BOP, CCI, CMO, DX,
          MACD, MACDEXT, MACDFIX, MFI, MINUS_DI, MINUS_DM,
          MOM, PLUS_DI, PLUS_DM, PPO, ROC, ROCP, ROCR, ROCR100,
          RSI, STOCH, STOCHF, STOCHRSI, TRIX, ULTOSC, WILLR
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')
        if not qs.exists():
            return error_response('无日频数据', 404)

        open_p, high_p, low_p, close_p, volume_p, dates = _build_ohlcv_arrays(qs)

        timeperiod = int(request.GET.get('timeperiod', 14))
        fastperiod = int(request.GET.get('fastperiod', 12))
        slowperiod = int(request.GET.get('slowperiod', 26))
        signalperiod = int(request.GET.get('signalperiod', 9))
        matype = int(request.GET.get('matype', 0))

        results = {}
        skipped = []

        def add_series(name, series_dict):
            results[name] = _build_output(dates, series_dict)

        # ADX / ADXR
        try:
            add_series('ADX', {'adx': talib.ADX(high_p, low_p, close_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'ADX', 'reason': str(e)})
        try:
            add_series('ADXR', {'adxr': talib.ADXR(high_p, low_p, close_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'ADXR', 'reason': str(e)})

        # APO
        try:
            add_series('APO', {'apo': talib.APO(close_p, fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)})
        except Exception as e:
            skipped.append({'indicator': 'APO', 'reason': str(e)})

        # AROON / AROONOSC
        try:
            aroondown, aroonup = talib.AROON(high_p, low_p, timeperiod=timeperiod)
            add_series('AROON', {'aroondown': aroondown, 'aroonup': aroonup})
        except Exception as e:
            skipped.append({'indicator': 'AROON', 'reason': str(e)})
        try:
            add_series('AROONOSC', {'aroonosc': talib.AROONOSC(high_p, low_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'AROONOSC', 'reason': str(e)})

        # BOP
        try:
            add_series('BOP', {'bop': talib.BOP(open_p, high_p, low_p, close_p)})
        except Exception as e:
            skipped.append({'indicator': 'BOP', 'reason': str(e)})

        # CCI, CMO, DX
        for name, arr_func in (
            ('CCI', lambda: talib.CCI(high_p, low_p, close_p, timeperiod=timeperiod)),
            ('CMO', lambda: talib.CMO(close_p, timeperiod=timeperiod)),
            ('DX', lambda: talib.DX(high_p, low_p, close_p, timeperiod=timeperiod)),
        ):
            try:
                arr = arr_func()
                add_series(name, {name.lower(): arr})
            except Exception as e:
                skipped.append({'indicator': name, 'reason': str(e)})

        # MACD *
        try:
            macd, macdsignal, macdhist = talib.MACD(close_p, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
            add_series('MACD', {'macd': macd, 'macdsignal': macdsignal, 'macdhist': macdhist})
        except Exception as e:
            skipped.append({'indicator': 'MACD', 'reason': str(e)})
        try:
            macd, macdsignal, macdhist = talib.MACDEXT(close_p, fastperiod=fastperiod, fastmatype=matype, slowperiod=slowperiod, slowmatype=matype, signalperiod=signalperiod, signalmatype=matype)
            add_series('MACDEXT', {'macd': macd, 'macdsignal': macdsignal, 'macdhist': macdhist})
        except Exception as e:
            skipped.append({'indicator': 'MACDEXT', 'reason': str(e)})
        try:
            macd, macdsignal, macdhist = talib.MACDFIX(close_p, signalperiod=signalperiod)
            add_series('MACDFIX', {'macd': macd, 'macdsignal': macdsignal, 'macdhist': macdhist})
        except Exception as e:
            skipped.append({'indicator': 'MACDFIX', 'reason': str(e)})

        # MFI
        try:
            add_series('MFI', {'mfi': talib.MFI(high_p, low_p, close_p, volume_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'MFI', 'reason': str(e)})

        # MINUS_DI / MINUS_DM / PLUS_DI / PLUS_DM
        for name, arr_func in (
            ('MINUS_DI', lambda: talib.MINUS_DI(high_p, low_p, close_p, timeperiod=timeperiod)),
            ('MINUS_DM', lambda: talib.MINUS_DM(high_p, low_p, timeperiod=timeperiod)),
            ('PLUS_DI', lambda: talib.PLUS_DI(high_p, low_p, close_p, timeperiod=timeperiod)),
            ('PLUS_DM', lambda: talib.PLUS_DM(high_p, low_p, timeperiod=timeperiod)),
        ):
            try:
                arr = arr_func()
                add_series(name, {name.lower(): arr})
            except Exception as e:
                skipped.append({'indicator': name, 'reason': str(e)})

        # MOM, PPO
        for name, arr_func in (
            ('MOM', lambda: talib.MOM(close_p, timeperiod=timeperiod)),
            ('PPO', lambda: talib.PPO(close_p, fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)),
        ):
            try:
                arr = arr_func()
                add_series(name, {name.lower(): arr})
            except Exception as e:
                skipped.append({'indicator': name, 'reason': str(e)})

        # ROC, ROCP, ROCR, ROCR100
        for name, func in (
            ('ROC', talib.ROC), ('ROCP', talib.ROCP), ('ROCR', talib.ROCR), ('ROCR100', talib.ROCR100)
        ):
            try:
                arr = func(close_p, timeperiod=timeperiod)
                add_series(name, {name.lower(): arr})
            except Exception as e:
                skipped.append({'indicator': name, 'reason': str(e)})

        # RSI
        try:
            add_series('RSI', {'rsi': talib.RSI(close_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'RSI', 'reason': str(e)})

        # STOCH, STOCHF, STOCHRSI
        try:
            fastk_period = int(request.GET.get('fastk_period', 5))
            slowk_period = int(request.GET.get('slowk_period', 3))
            slowd_period = int(request.GET.get('slowd_period', 3))
            slowk_matype = int(request.GET.get('slowk_matype', 0))
            slowd_matype = int(request.GET.get('slowd_matype', 0))
            slowk, slowd = talib.STOCH(
                high_p, low_p, close_p,
                fastk_period=fastk_period,
                slowk_period=slowk_period,
                slowd_period=slowd_period,
                slowk_matype=slowk_matype,
                slowd_matype=slowd_matype,
            )
            add_series('STOCH', {'slowk': slowk, 'slowd': slowd})
        except Exception as e:
            skipped.append({'indicator': 'STOCH', 'reason': str(e)})
        try:
            fastk_period = int(request.GET.get('fastk_period', 5))
            fastd_period = int(request.GET.get('fastd_period', 3))
            fastd_matype = int(request.GET.get('fastd_matype', 0))
            fastk, fastd = talib.STOCHF(
                high_p, low_p, close_p,
                fastk_period=fastk_period,
                fastd_period=fastd_period,
                fastd_matype=fastd_matype,
            )
            add_series('STOCHF', {'fastk': fastk, 'fastd': fastd})
        except Exception as e:
            skipped.append({'indicator': 'STOCHF', 'reason': str(e)})
        try:
            fastk_period = int(request.GET.get('fastk_period', 5))
            fastd_period = int(request.GET.get('fastd_period', 3))
            fastd_matype = int(request.GET.get('fastd_matype', 0))
            fastk, fastd = talib.STOCHRSI(close_p, timeperiod=timeperiod, fastk_period=fastk_period, fastd_period=fastd_period, fastd_matype=fastd_matype)
            add_series('STOCHRSI', {'fastk': fastk, 'fastd': fastd})
        except Exception as e:
            skipped.append({'indicator': 'STOCHRSI', 'reason': str(e)})

        # TRIX
        try:
            add_series('TRIX', {'trix': talib.TRIX(close_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'TRIX', 'reason': str(e)})

        # ULTOSC
        try:
            timeperiod1 = int(request.GET.get('timeperiod1', 7))
            timeperiod2 = int(request.GET.get('timeperiod2', 14))
            timeperiod3 = int(request.GET.get('timeperiod3', 28))
            arr = talib.ULTOSC(high_p, low_p, close_p, timeperiod1=timeperiod1, timeperiod2=timeperiod2, timeperiod3=timeperiod3)
            add_series('ULTOSC', {'ultosc': arr})
        except Exception as e:
            skipped.append({'indicator': 'ULTOSC', 'reason': str(e)})

        # WILLR
        try:
            add_series('WILLR', {'willr': talib.WILLR(high_p, low_p, close_p, timeperiod=timeperiod)})
        except Exception as e:
            skipped.append({'indicator': 'WILLR', 'reason': str(e)})

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'category': 'momentum',
            'indicators': results,
            'skipped': skipped,
            'total': len(dates)
        }
        return success_response(data, '计算动量指标成功')
    except Exception as e:
        return error_response(f'计算动量指标失败: {str(e)}', 500)


# ========= 分类指标API：成交量指标 =========
@csrf_exempt
@require_http_methods(["GET"])
def analyze_volume_indicators(request, stock_code: str):
    """
    成交量类指标计算接口
    返回该类别下所有可计算指标的结果
    支持: AD, ADOSC, OBV
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')
        if not qs.exists():
            return error_response('无日频数据', 404)

        open_p, high_p, low_p, close_p, volume_p, dates = _build_ohlcv_arrays(qs)

        results = {}
        skipped = []

        # AD
        try:
            arr = talib.AD(high_p, low_p, close_p, volume_p)
            results['AD'] = _build_output(dates, {'ad': arr})
        except Exception as e:
            skipped.append({'indicator': 'AD', 'reason': str(e)})

        # ADOSC
        try:
            fastperiod = int(request.GET.get('fastperiod', 3))
            slowperiod = int(request.GET.get('slowperiod', 10))
            arr = talib.ADOSC(high_p, low_p, close_p, volume_p, fastperiod=fastperiod, slowperiod=slowperiod)
            results['ADOSC'] = _build_output(dates, {'adosc': arr})
        except Exception as e:
            skipped.append({'indicator': 'ADOSC', 'reason': str(e)})

        # OBV
        try:
            arr = talib.OBV(close_p, volume_p)
            results['OBV'] = _build_output(dates, {'obv': arr})
        except Exception as e:
            skipped.append({'indicator': 'OBV', 'reason': str(e)})

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'category': 'volume',
            'indicators': results,
            'skipped': skipped,
            'total': len(dates)
        }
        return success_response(data, '计算成交量指标成功')
    except Exception as e:
        return error_response(f'计算成交量指标失败: {str(e)}', 500)


# ========= 分类指标API：波动率指标 =========
@csrf_exempt
@require_http_methods(["GET"])
def analyze_volatility_indicators(request, stock_code: str):
    """
    波动率类指标计算接口
    返回该类别下所有可计算指标的结果
    支持: ATR, NATR, TRANGE
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')
        if not qs.exists():
            return error_response('无日频数据', 404)

        open_p, high_p, low_p, close_p, volume_p, dates = _build_ohlcv_arrays(qs)

        timeperiod = int(request.GET.get('timeperiod', 14))

        results = {}
        skipped = []

        try:
            arr = talib.ATR(high_p, low_p, close_p, timeperiod=timeperiod)
            results['ATR'] = _build_output(dates, {'atr': arr})
        except Exception as e:
            skipped.append({'indicator': 'ATR', 'reason': str(e)})
        try:
            arr = talib.NATR(high_p, low_p, close_p, timeperiod=timeperiod)
            results['NATR'] = _build_output(dates, {'natr': arr})
        except Exception as e:
            skipped.append({'indicator': 'NATR', 'reason': str(e)})
        try:
            arr = talib.TRANGE(high_p, low_p, close_p)
            results['TRANGE'] = _build_output(dates, {'trange': arr})
        except Exception as e:
            skipped.append({'indicator': 'TRANGE', 'reason': str(e)})

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'category': 'volatility',
            'indicators': results,
            'skipped': skipped,
            'total': len(dates)
        }
        return success_response(data, '计算波动率指标成功')
    except Exception as e:
        return error_response(f'计算波动率指标失败: {str(e)}', 500)


# ========= 分类指标API：价格变换 =========
@csrf_exempt
@require_http_methods(["GET"])
def analyze_price_transform_indicators(request, stock_code: str):
    """
    价格变换类指标计算接口
    返回该类别下所有可计算指标的结果
    支持: AVGPRICE, MEDPRICE, TYPPRICE, WCLPRICE
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')
        if not qs.exists():
            return error_response('无日频数据', 404)

        open_p, high_p, low_p, close_p, volume_p, dates = _build_ohlcv_arrays(qs)

        results = {}
        skipped = []

        for name, func, series_name in (
            ('AVGPRICE', talib.AVGPRICE, 'avgprice'),
            ('MEDPRICE', talib.MEDPRICE, 'medprice'),
            ('TYPPRICE', talib.TYPPRICE, 'typprice'),
            ('WCLPRICE', talib.WCLPRICE, 'wclprice'),
        ):
            try:
                if name == 'AVGPRICE':
                    arr = func(open_p, high_p, low_p, close_p)
                elif name == 'MEDPRICE':
                    arr = func(high_p, low_p)
                else:
                    arr = func(high_p, low_p, close_p)
                results[name] = _build_output(dates, {series_name: arr})
            except Exception as e:
                skipped.append({'indicator': name, 'reason': str(e)})

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'category': 'price_transform',
            'indicators': results,
            'skipped': skipped,
            'total': len(dates)
        }
        return success_response(data, '计算价格变换指标成功')
    except Exception as e:
        return error_response(f'计算价格变换指标失败: {str(e)}', 500)


# ========= 分类指标API：周期指标 =========
@csrf_exempt
@require_http_methods(["GET"])
def analyze_cycle_indicators(request, stock_code: str):
    """
    周期/希尔伯特变换类指标计算接口
    返回该类别下所有可计算指标的结果
    支持: HT_DCPERIOD, HT_DCPHASE, HT_PHASOR, HT_SINE, HT_TRENDMODE
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            stock = IndividualStock.objects.get(code=stock_code)
        except IndividualStock.DoesNotExist:
            return error_response(f'股票代码不存在: {stock_code}', 404)

        qs = IndividualStockDaily.objects.filter(stock=stock)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        qs = qs.order_by('date')
        if not qs.exists():
            return error_response('无日频数据', 404)

        open_p, high_p, low_p, close_p, volume_p, dates = _build_ohlcv_arrays(qs)

        results = {}
        skipped = []

        try:
            arr = talib.HT_DCPERIOD(close_p)
            results['HT_DCPERIOD'] = _build_output(dates, {'ht_dcperiod': arr})
        except Exception as e:
            skipped.append({'indicator': 'HT_DCPERIOD', 'reason': str(e)})
        try:
            arr = talib.HT_DCPHASE(close_p)
            results['HT_DCPHASE'] = _build_output(dates, {'ht_dcphase': arr})
        except Exception as e:
            skipped.append({'indicator': 'HT_DCPHASE', 'reason': str(e)})
        try:
            inphase, quadrature = talib.HT_PHASOR(close_p)
            results['HT_PHASOR'] = _build_output(dates, {'inphase': inphase, 'quadrature': quadrature})
        except Exception as e:
            skipped.append({'indicator': 'HT_PHASOR', 'reason': str(e)})
        try:
            sine, leadsine = talib.HT_SINE(close_p)
            results['HT_SINE'] = _build_output(dates, {'sine': sine, 'leadsine': leadsine})
        except Exception as e:
            skipped.append({'indicator': 'HT_SINE', 'reason': str(e)})
        try:
            arr = talib.HT_TRENDMODE(close_p)
            results['HT_TRENDMODE'] = _build_output(dates, {'ht_trendmode': arr})
        except Exception as e:
            skipped.append({'indicator': 'HT_TRENDMODE', 'reason': str(e)})

        data = {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'category': 'cycle',
            'indicators': results,
            'skipped': skipped,
            'total': len(dates)
        }
        return success_response(data, '计算周期指标成功')
    except Exception as e:
        return error_response(f'计算周期指标失败: {str(e)}', 500)