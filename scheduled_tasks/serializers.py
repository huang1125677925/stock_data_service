from rest_framework import serializers




class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    error = serializers.CharField(required=False)


class GitCommitRecordSerializer(serializers.Serializer):
    # commit_id = serializers.CharField(required=False)
    authored_datetime = serializers.CharField(required=False)
    # author_name = serializers.CharField(required=False)
    message = serializers.CharField(required=False)


class GitInfoDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = GitCommitRecordSerializer(many=True)


class SuccessResponseGitInfoSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = GitInfoDataSerializer()


# --- DC 概念/行业/地域板块日频行情（dc_daily） ---
class DcDailyRecordSerializer(serializers.Serializer):
    """
    dc_daily 记录字段序列化器

    字段说明参考 Tushare 文档：东财概念板块、行业指数板块、地域板块日频行情。
    """
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    close = serializers.FloatField(required=False)
    open = serializers.FloatField(required=False)
    high = serializers.FloatField(required=False)
    low = serializers.FloatField(required=False)
    change = serializers.FloatField(required=False)
    pct_change = serializers.FloatField(required=False)
    vol = serializers.FloatField(required=False)
    amount = serializers.FloatField(required=False)
    swing = serializers.FloatField(required=False)
    turnover_rate = serializers.FloatField(required=False)


class DcDailyDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = DcDailyRecordSerializer(many=True)


class SuccessResponseDcDailySerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = DcDailyDataSerializer()


# --- 东方财富概念板块（dc_index） ---
class DcIndexRecordSerializer(serializers.Serializer):
    """
    dc_index 记录字段序列化器

    字段说明参考 Tushare 文档：东方财富概念板块。
    """
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    leading = serializers.CharField(required=False)
    leading_code = serializers.CharField(required=False)
    pct_change = serializers.FloatField(required=False)
    leading_pct = serializers.FloatField(required=False)
    total_mv = serializers.FloatField(required=False)
    turnover_rate = serializers.FloatField(required=False)
    up_num = serializers.IntegerField(required=False)
    down_num = serializers.IntegerField(required=False)


class DcIndexDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = DcIndexRecordSerializer(many=True)


class SuccessResponseDcIndexSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = DcIndexDataSerializer()


# --- AH股比价（stk_ah_comparison） ---
class AhComparisonRecordSerializer(serializers.Serializer):
    """
    stk_ah_comparison 记录字段序列化器

    字段参考文档：AH股比价。
    """
    hk_code = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    hk_name = serializers.CharField(required=False)
    hk_pct_chg = serializers.FloatField(required=False)
    hk_close = serializers.FloatField(required=False)
    name = serializers.CharField(required=False)
    close = serializers.FloatField(required=False)
    pct_chg = serializers.FloatField(required=False)
    ah_comparison = serializers.FloatField(required=False)
    ah_premium = serializers.FloatField(required=False)


class AhComparisonDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = AhComparisonRecordSerializer(many=True)


class SuccessResponseAhComparisonSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = AhComparisonDataSerializer()


# --- 券商月度金股（broker_recommend） ---
class BrokerRecommendRecordSerializer(serializers.Serializer):
    """
    broker_recommend 记录字段序列化器

    字段参考文档：券商每月荐股。
    """
    month = serializers.CharField(required=False)
    broker = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)


class BrokerRecommendDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = BrokerRecommendRecordSerializer(many=True)


class SuccessResponseBrokerRecommendSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = BrokerRecommendDataSerializer()


# --- 中央结算系统持股明细（ccass_hold_detail） ---
class CcassHoldDetailRecordSerializer(serializers.Serializer):
    """
    ccass_hold_detail 记录字段序列化器

    字段参考文档：中央结算系统持股明细。
    """
    trade_date = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    col_participant_id = serializers.CharField(required=False)
    col_participant_name = serializers.CharField(required=False)
    col_shareholding = serializers.CharField(required=False)
    col_shareholding_percent = serializers.CharField(required=False)


class CcassHoldDetailDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = CcassHoldDetailRecordSerializer(many=True)


class SuccessResponseCcassHoldDetailSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = CcassHoldDetailDataSerializer()


# --- 中央结算系统持股汇总（ccass_hold） ---
class CcassHoldRecordSerializer(serializers.Serializer):
    """
    ccass_hold 记录字段序列化器

    字段参考文档：中央结算系统持股汇总。
    """
    trade_date = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    shareholding = serializers.CharField(required=False)
    hold_nums = serializers.CharField(required=False)
    hold_ratio = serializers.CharField(required=False)


class CcassHoldDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = CcassHoldRecordSerializer(many=True)


class SuccessResponseCcassHoldSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = CcassHoldDataSerializer()


# --- 连板天梯（limit_step） ---
class LimitStepRecordSerializer(serializers.Serializer):
    """
    limit_step 记录字段序列化器

    字段参考文档：涨停股票连板天梯。
    """
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    nums = serializers.CharField(required=False)


class LimitStepDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = LimitStepRecordSerializer(many=True)


class SuccessResponseLimitStepSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = LimitStepDataSerializer()


# --- 游资每日明细（hm_detail） ---
class HmDetailRecordSerializer(serializers.Serializer):
    """
    hm_detail 记录字段序列化器

    字段参考文档：游资交易每日明细。
    """
    trade_date = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    ts_name = serializers.CharField(required=False)
    buy_amount = serializers.FloatField(required=False)
    sell_amount = serializers.FloatField(required=False)
    net_amount = serializers.FloatField(required=False)
    hm_name = serializers.CharField(required=False)
    hm_orgs = serializers.CharField(required=False)
    tag = serializers.CharField(required=False)


class HmDetailDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = HmDetailRecordSerializer(many=True)


class SuccessResponseHmDetailSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = HmDetailDataSerializer()


# --- 沪深港股通持股明细（hk_hold） ---
class HkHoldRecordSerializer(serializers.Serializer):
    """
    hk_hold 记录字段序列化器

    功能：序列化沪深港股通持股明细记录。
    参数：无（字段来自Tushare返回记录）。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    vol = serializers.IntegerField(required=False)
    ratio = serializers.FloatField(required=False)
    exchange = serializers.CharField(required=False)


class HkHoldDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = HkHoldRecordSerializer(many=True)


class SuccessResponseHkHoldSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = HkHoldDataSerializer()


# --- 沪深港通股票列表（stock_hsgt） ---
class StockHsgtRecordSerializer(serializers.Serializer):
    """
    stock_hsgt 记录字段序列化器

    功能：序列化沪深港通股票列表记录。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    type_name = serializers.CharField(required=False)


class StockHsgtDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = StockHsgtRecordSerializer(many=True)


class SuccessResponseStockHsgtSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = StockHsgtDataSerializer()


# --- 沪深股通十大成交股（hsgt_top10） ---
class HsgtTop10RecordSerializer(serializers.Serializer):
    """
    hsgt_top10 记录字段序列化器

    功能：序列化每日前十大成交股记录。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    trade_date = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    close = serializers.FloatField(required=False)
    change = serializers.FloatField(required=False)
    rank = serializers.IntegerField(required=False)
    market_type = serializers.CharField(required=False)
    amount = serializers.FloatField(required=False)
    net_amount = serializers.FloatField(required=False)
    buy = serializers.FloatField(required=False)
    sell = serializers.FloatField(required=False)


class HsgtTop10DataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = HsgtTop10RecordSerializer(many=True)


class SuccessResponseHsgtTop10Serializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = HsgtTop10DataSerializer()


# --- 上证E互动问答（irm_qa_sh） ---
class IrmQaShRecordSerializer(serializers.Serializer):
    """
    irm_qa_sh 记录字段序列化器

    功能：序列化上证e互动问答记录。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    q = serializers.CharField(required=False)
    a = serializers.CharField(required=False)
    pub_time = serializers.CharField(required=False)


class IrmQaShDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IrmQaShRecordSerializer(many=True)


class SuccessResponseIrmQaShSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IrmQaShDataSerializer()


# --- 深证互动易问答（irm_qa_sz） ---
class IrmQaSzRecordSerializer(serializers.Serializer):
    """
    irm_qa_sz 记录字段序列化器

    功能：序列化深证互动易问答记录。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    q = serializers.CharField(required=False)
    a = serializers.CharField(required=False)
    pub_time = serializers.CharField(required=False)
    industry = serializers.CharField(required=False)


class IrmQaSzDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IrmQaSzRecordSerializer(many=True)


class SuccessResponseIrmQaSzSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IrmQaSzDataSerializer()


# --- 每日筹码及胜率（cyq_perf） ---
class CyqPerfRecordSerializer(serializers.Serializer):
    """
    cyq_perf 记录字段序列化器

    功能：序列化每日筹码及胜率记录。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    his_low = serializers.FloatField(required=False)
    his_high = serializers.FloatField(required=False)
    cost_5pct = serializers.FloatField(required=False)
    cost_15pct = serializers.FloatField(required=False)
    cost_50pct = serializers.FloatField(required=False)
    cost_85pct = serializers.FloatField(required=False)
    cost_95pct = serializers.FloatField(required=False)
    weight_avg = serializers.FloatField(required=False)
    winner_rate = serializers.FloatField(required=False)


class CyqPerfDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = CyqPerfRecordSerializer(many=True)


class SuccessResponseCyqPerfSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = CyqPerfDataSerializer()



