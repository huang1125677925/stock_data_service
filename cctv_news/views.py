from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import CCTVNews
from datetime import datetime
import logging
import json
from .services import news_service
from common.response import success_response, error_response
from common.validators import validate_pagination_params

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def get_news_list(request):
    """获取新闻列表"""
    try:
        # 获取查询参数
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        
        # 验证分页参数
        limit, _ = validate_pagination_params(limit, 0)
        
        # 获取新闻列表
        news_data = news_service.get_news_list(page, limit)
        if news_data is None:
            return error_response('获取新闻列表失败', 500)
        
        # 计算总数和分页信息
        total = CCTVNews.objects.count()
        has_next = (page * limit) < total
        
        return success_response(
            data={
                'news': news_data,
                'total': total,
                'page': page,
                'limit': limit,
                'has_next': has_next
            },
            message='获取新闻列表成功'
        )
        
    except Exception as e:
        logger.error(f"获取新闻列表失败: {str(e)}")
        return error_response('获取新闻列表失败', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_news_detail(request, news_id):
    """获取新闻详情"""
    try:
        news_detail = news_service.get_news_detail(int(news_id))
        if news_detail is None:
            return error_response('新闻不存在', 404)
        
        return success_response(news_detail, '获取新闻详情成功')
        
    except ValueError:
        return error_response('无效的新闻ID', 400)
    except Exception as e:
        logger.error(f"获取新闻详情失败: {str(e)}")
        return error_response('获取新闻详情失败', 500)

@csrf_exempt
@require_http_methods(["POST"])
def create_news(request):
    """创建新闻"""
    try:
        data = json.loads(request.body)
        
        # 验证必需字段
        required_fields = ['title', 'content']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'缺少必需字段: {field}', 400)
        
        # 创建新闻
        result = news_service.create_news(data)
        if result is None:
            return error_response('创建新闻失败', 500)
        
        if 'errors' in result:
            return error_response('新闻内容验证失败', 400, errors=result['errors'])
        
        return success_response(result, '创建新闻成功')
        
    except json.JSONDecodeError:
        return error_response('无效的JSON格式', 400)
    except Exception as e:
        logger.error(f"创建新闻失败: {str(e)}")
        return error_response('创建新闻失败', 500)

@csrf_exempt
@require_http_methods(["PUT"])
def update_news(request, news_id):
    """更新新闻"""
    try:
        data = json.loads(request.body)
        
        result = news_service.update_news(int(news_id), data)
        if result is None:
            return error_response('新闻不存在或更新失败', 404)
        
        return success_response(result, '更新新闻成功')
        
    except ValueError:
        return error_response('无效的新闻ID', 400)
    except json.JSONDecodeError:
        return error_response('无效的JSON格式', 400)
    except Exception as e:
        logger.error(f"更新新闻失败: {str(e)}")
        return error_response('更新新闻失败', 500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_news(request, news_id):
    """删除新闻"""
    try:
        result = news_service.delete_news(int(news_id))
        if not result:
            return error_response('新闻不存在或删除失败', 404)
        
        return success_response({'id': news_id}, '删除新闻成功')
        
    except ValueError:
        return error_response('无效的新闻ID', 400)
    except Exception as e:
        logger.error(f"删除新闻失败: {str(e)}")
        return error_response('删除新闻失败', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_latest_news(request):
    """获取最新新闻"""
    try:
        limit = int(request.GET.get('limit', 5))
        
        # 验证分页参数
        limit, _ = validate_pagination_params(limit, 0)
        
        # 获取最新新闻
        news_data = news_service.get_latest_news(limit)
        if news_data is None:
            return error_response('获取最新新闻失败', 500)
        
        return success_response(news_data, '获取最新新闻成功')
        
    except Exception as e:
        logger.error(f"获取最新新闻失败: {str(e)}")
        return error_response('获取最新新闻失败', 500)

@csrf_exempt
@require_http_methods(["GET"])
def search_news(request):
    """搜索新闻"""
    try:
        keyword = request.GET.get('keyword')
        limit = int(request.GET.get('limit', 20))
        
        if not keyword:
            return error_response('搜索关键词不能为空', 400)
        
        # 验证分页参数
        limit, _ = validate_pagination_params(limit, 0)
        
        # 搜索新闻
        news_data = news_service.search_news(keyword, limit)
        if news_data is None:
            return error_response('搜索新闻失败', 500)
        
        return success_response(news_data, '搜索新闻成功')
        
    except Exception as e:
        logger.error(f"搜索新闻失败: {str(e)}")
        return error_response('搜索新闻失败', 500)