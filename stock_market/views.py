from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .services import get_sse_daily_overview
import logging
from common.response import success_response, error_response

logger = logging.getLogger(__name__)

class SSEDailyOverviewView(APIView):
    """
    获取上海证券交易所每日概况数据的API视图
    """
    def get(self, request):
        """
        获取上证每日概况数据
        
        参数:
            date (str, optional): 日期，格式为YYYYMMDD，默认为最近一个交易日
        """
        try:
            date = request.query_params.get('date')
            result = get_sse_daily_overview(date)
            return success_response(result)
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取上证每日概况数据失败: {str(e)}")
            return error_response(f'获取上证每日概况数据失败: {str(e)}', 500)
