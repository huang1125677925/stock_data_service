from django.urls import path
from . import views

urlpatterns = [
    path('index-rps/', views.get_index_rps, name='get_index_rps'),
    path('stock-rps/', views.get_stock_rps, name='get_stock_rps'),
    path('major-index-rps/', views.get_major_index_rps, name='get_major_index_rps'),
    path('dc-board-member-rps/', views.get_dc_board_member_rps, name='get_dc_board_member_rps'),
    path('industry-turnover-percentile/', views.get_industry_turnover_percentile, name='get_industry_turnover_percentile'),
    path('industry-ma-breadth/', views.get_industry_ma_breadth, name='get_industry_ma_breadth'),
    path('industry-up-down-ratio/', views.get_industry_up_down_ratio, name='get_industry_up_down_ratio'),
    path('limit-board/daily-sentiment/', views.get_limit_board_daily_sentiment, name='get_limit_board_daily_sentiment'),
    path('limit-board/auction-candidates/', views.get_enhanced_auction_candidates, name='get_enhanced_auction_candidates'),
    path('limit-board/theme-ladder/', views.get_limit_board_theme_ladder, name='get_limit_board_theme_ladder'),
    path('limit-board/break-reseal/', views.get_limit_board_break_reseal, name='get_limit_board_break_reseal'),
    path('limit-board/hot-money-review/', views.get_limit_board_hot_money_review, name='get_limit_board_hot_money_review'),
    path('limit-board/industry-trend-strength/', views.get_limit_board_industry_trend_strength, name='get_limit_board_industry_trend_strength'),
    path('swing-analysis/', views.get_swing_analysis, name='get_swing_analysis'),
    path('swing-channel-candidates/', views.get_swing_channel_candidates, name='get_swing_channel_candidates'),
]
