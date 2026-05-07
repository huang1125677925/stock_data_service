from django.urls import path
from . import views
from .individual_analysis.views import analyze_candlestick_patterns, analyze_overlap_indicators, analyze_momentum_indicators, analyze_volume_indicators, analyze_volatility_indicators, analyze_price_transform_indicators, analyze_cycle_indicators
from .market_analysis.views import get_market_adr, get_market_adl, get_market_nh_nl

urlpatterns = [
    path('index-rps/', views.get_index_rps, name='get_index_rps'),
    path('historical-rps/', views.get_historical_rps, name='get_historical_rps'),
    path('industry-turnover-percentile/', views.get_industry_turnover_percentile, name='get_industry_turnover_percentile'),
    path('screen-stocks/', views.screen_stocks_by_previous_high, name='screen_stocks_by_previous_high'),
    path('execute-tagging-task/', views.execute_stock_tagging_task, name='execute_stock_tagging_task'),
    path('stock-analysis/<str:stock_code>/', views.get_stock_analysis_detail, name='get_stock_analysis_detail'),
    path('industry-ma-breadth/', views.get_industry_ma_breadth, name='get_industry_ma_breadth'),
    path('industry-scale-breadth/', views.get_industry_scale_breadth, name='get_industry_scale_breadth'),
    path('industry-actual-output/', views.get_industry_actual_output, name='get_industry_actual_output'),
    path('industry-fund-flow-correlation/', views.get_industry_fund_flow_correlation, name='get_industry_fund_flow_correlation'),
    path('individual-analysis/candlestick/<str:stock_code>/', analyze_candlestick_patterns, name='analyze_candlestick_patterns'),
    # 新增：大盘分析市场宽度相关接口
    path('market-analysis/adr/', get_market_adr, name='get_market_adr'),
    path('market-analysis/adl/', get_market_adl, name='get_market_adl'),
    path('market-analysis/nh-nl/', get_market_nh_nl, name='get_market_nh_nl'),
    # 新增TA-Lib分类指标API
    path('individual-analysis/overlap/<str:stock_code>/', analyze_overlap_indicators, name='analyze_overlap_indicators'),
    path('individual-analysis/momentum/<str:stock_code>/', analyze_momentum_indicators, name='analyze_momentum_indicators'),
    path('individual-analysis/volume/<str:stock_code>/', analyze_volume_indicators, name='analyze_volume_indicators'),
    path('individual-analysis/volatility/<str:stock_code>/', analyze_volatility_indicators, name='analyze_volatility_indicators'),
    path('individual-analysis/price-transform/<str:stock_code>/', analyze_price_transform_indicators, name='analyze_price_transform_indicators'),
    path('individual-analysis/cycle/<str:stock_code>/', analyze_cycle_indicators, name='analyze_cycle_indicators'),
    # MACD XGBoost预测接口
    path('index-analysis/macd-up-prediction/<str:stock_code>/', views.IndexMacdXgbGrowthDatesView.as_view(), name='get_index_macd_xgb_growth_dates'),
    # 选股记录查询：5日实际上涨比例（APIView实现）
    path('individual-analysis/actual-rise-ratio/', views.ActualRiseRatio5DView.as_view(), name='get_actual_rise_ratio_5d'),
]