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
from common.validators import validate_date_range
from collections import Counter
from .sensitive_word_filter import SensitiveWordFilter
import re
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

@csrf_exempt
@require_http_methods(["GET"])
def get_ai_content_wordcloud(request):
    """按日期范围统计AI分析内容词频，用于词云展示
    请求参数：
    - start_date: 开始日期，格式YYYY-MM-DD
    - end_date: 结束日期，格式YYYY-MM-DD
    - top_n: 返回前多少个高频词（可选，默认100，最大500）
    - min_len: 词最小长度过滤（可选，默认2）
    返回：统一success_response，包含words列表 [{word, count}] 及查询信息
    """
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        top_n = int(request.GET.get('top_n', 100))
        min_len = int(request.GET.get('min_len', 2))

        if not start_date or not end_date:
            return error_response('start_date 和 end_date 为必填参数', 400)
        if not validate_date_range(start_date, end_date):
            return error_response('日期范围不合法，格式应为YYYY-MM-DD，且开始日期不晚于结束日期', 400)
        if top_n <= 0:
            top_n = 100
        if top_n > 500:
            top_n = 500
        if min_len < 1:
            min_len = 1

        # 查询指定日期范围内的AI内容
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        queryset = CCTVNews.objects.filter(
            publish_date__gte=start,
            publish_date__lte=end,
        ).exclude(ai_content__isnull=True).exclude(ai_content__exact='')
        sensitive_word_filter = SensitiveWordFilter()
        contents = [sensitive_word_filter.filter_text(n.ai_content) for n in queryset]
        if not contents:
            return success_response({
                'total': 0,
                'words': [],
                'query': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'top_n': top_n,
                    'min_len': min_len
                }
            }, '指定日期范围内无AI内容')

        # 合并文本
        text = '\n'.join(contents)

        # 尝试使用jieba分词，不存在时回退到简单中文字符分块
        try:
            import jieba
            words = jieba.lcut(text)
        except Exception:
            # 回退：将连续中文字符作为词
            words = re.findall(r'[\u4e00-\u9fff]{%d,}' % max(min_len, 2), text)

        # 基础停用词与清洗（可按需扩展）
        stop_words = set(['的', '了', '和', '是', '在', '就', '都', '而', '及', '与', '著', '或', '一个', '我们', '你们', '他们', '因为', '所以', '通过', '以及'])
        # 保留中文、英文、数字组合的简单词，去除纯标点
        cleaned = []
        for w in words:
            w = w.strip()
            # 移除非中文、字母、数字的字符
            w = re.sub(r'[^\w\u4e00-\u9fff]+', '', w)
            if not w:
                continue
            if len(w) < min_len:
                continue
            if w in stop_words:
                continue
            cleaned.append(w)

        if not cleaned:
            return success_response({
                'total': 0,
                'words': [],
                'query': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'top_n': top_n,
                    'min_len': min_len
                }
            }, '经过过滤后无有效词')

        counts = Counter(cleaned)
        top_items = counts.most_common(top_n)

        words_data = [{'word': w, 'count': int(c)} for w, c in top_items]

        return success_response({
            'total': len(counts),
            'words': words_data,
            'query': {
                'start_date': start_date,
                'end_date': end_date,
                'top_n': top_n,
                'min_len': min_len
            }
        }, '获取AI内容词频成功')

    except ValueError:
        return error_response('参数格式错误：top_n/min_len需为整数', 400)
    except Exception as e:
        logger.error(f"获取AI内容词频失败: {str(e)}")
        return error_response('获取AI内容词频失败', 500)