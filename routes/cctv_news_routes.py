# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from utils.response import success_response, error_response
from models.cctv_news_model import CCTVNewsModel
from datetime import datetime
import logging

# 创建蓝图
bp = Blueprint('cctv_news', __name__, url_prefix='/api/cctv_news')


@bp.route('/', methods=['GET'])
def get_news_list():
    """获取新闻列表
    
    Query Parameters:
        limit: 返回结果数量限制，默认10
        offset: 分页偏移量，默认0
        keyword: 搜索关键词（可选）
    
    Returns:
        新闻列表JSON
    """
    try:
        limit = request.args.get('limit', default=10, type=int)
        offset = request.args.get('offset', default=0, type=int)
        keyword = request.args.get('keyword', default=None, type=str)
        
        if keyword:
            # 关键词搜索
            news_list = CCTVNewsModel.objects.search_by_keyword(keyword, limit=limit)
        else:
            # 获取所有新闻，按发布日期倒序排列
            news_list = CCTVNewsModel.objects.all(limit=limit, offset=offset, order_by="publish_date DESC")
        
        # 转换为字典列表
        result = [news.to_dict() for news in news_list]
        
        # 获取总数
        total_count = CCTVNewsModel.objects.count()
        
        return success_response({
            'total': total_count,
            'items': result,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取新闻列表失败: {str(e)}")
        return error_response(f'获取新闻列表失败: {str(e)}', 500)


@bp.route('/<int:news_id>', methods=['GET'])
def get_news_detail(news_id):
    """获取新闻详情
    
    Args:
        news_id: 新闻ID
    
    Returns:
        新闻详情JSON
    """
    try:
        news = CCTVNewsModel.objects.get(id=news_id)
        
        if not news:
            return error_response('新闻不存在', 404)
        
        return success_response(news.to_dict())
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取新闻详情失败: {str(e)}")
        return error_response(f'获取新闻详情失败: {str(e)}', 500)


@bp.route('/', methods=['POST'])
def create_news():
    """创建新闻
    
    Request Body:
        {
            "title": "新闻标题",
            "content": "新闻内容",
            "ai_content": "AI处理后的内容（可选）",
            "publish_date": "2024-01-01" (可选，默认当前日期)
        }
    
    Returns:
        创建的新闻对象
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('title'):
            return error_response('新闻标题不能为空', 400)
        if not data.get('content'):
            return error_response('新闻内容不能为空', 400)
        
        # 处理发布日期
        publish_date = data.get('publish_date')
        if publish_date:
            try:
                publish_date = datetime.strptime(publish_date, '%Y-%m-%d')
            except ValueError:
                return error_response('发布日期格式错误，应为YYYY-MM-DD', 400)
        else:
            publish_date = datetime.now().date()
        
        # 创建新闻对象
        news = CCTVNewsModel(
            title=data.get('title'),
            content=data.get('content'),
            ai_content=data.get('ai_content'),
            publish_date=publish_date
        )
        
        # 保存到数据库
        news.save()
        
        return success_response({
            'message': '新闻创建成功',
            'news': news.to_dict()
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"创建新闻失败: {str(e)}")
        return error_response(f'创建新闻失败: {str(e)}', 500)


@bp.route('/<int:news_id>', methods=['PUT'])
def update_news(news_id):
    """更新新闻
    
    Args:
        news_id: 新闻ID
    
    Request Body:
        {
            "title": "更新的标题",
            "content": "更新的内容",
            "ai_content": "更新的AI内容",
            "publish_date": "2024-01-01"
        }
    
    Returns:
        更新后的新闻对象
    """
    try:
        data = request.get_json()
        
        # 获取要更新的新闻
        news = CCTVNewsModel.objects.get(id=news_id)
        
        if not news:
            return error_response('新闻不存在', 404)
        
        # 更新字段
        if 'title' in data:
            news.title = data['title']
        if 'content' in data:
            news.content = data['content']
        if 'ai_content' in data:
            news.ai_content = data['ai_content']
        if 'publish_date' in data:
            try:
                news.publish_date = datetime.strptime(data['publish_date'], '%Y-%m-%d')
            except ValueError:
                return error_response('发布日期格式错误，应为YYYY-MM-DD', 400)
        
        # 保存更新
        news.save()
        
        return success_response({
            'message': '新闻更新成功',
            'news': news.to_dict()
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"更新新闻失败: {str(e)}")
        return error_response(f'更新新闻失败: {str(e)}', 500)


@bp.route('/<int:news_id>', methods=['DELETE'])
def delete_news(news_id):
    """删除新闻
    
    Args:
        news_id: 新闻ID
    
    Returns:
        删除结果
    """
    try:
        # 获取要删除的新闻
        news = CCTVNewsModel.objects.get(id=news_id)
        
        if not news:
            return error_response('新闻不存在', 404)
        
        # 删除新闻
        news.delete()
        
        return success_response({
            'message': '新闻删除成功',
            'id': news_id
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"删除新闻失败: {str(e)}")
        return error_response(f'删除新闻失败: {str(e)}', 500)


@bp.route('/latest', methods=['GET'])
def get_latest_news():
    """获取最新新闻
    
    Query Parameters:
        limit: 返回结果数量限制，默认5
    
    Returns:
        最新新闻列表
    """
    try:
        limit = request.args.get('limit', default=5, type=int)
        
        # 获取最新新闻
        news_list = CCTVNewsModel.objects.get_latest_news(limit=limit)
        
        # 转换为字典列表
        result = [news.to_dict() for news in news_list]
        
        return success_response({
            'total': len(result),
            'items': result
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取最新新闻失败: {str(e)}")
        return error_response(f'获取最新新闻失败: {str(e)}', 500)


@bp.route('/search', methods=['GET'])
def search_news():
    """搜索新闻
    
    Query Parameters:
        keyword: 搜索关键词
        limit: 返回结果数量限制，默认20
    
    Returns:
        搜索结果列表
    """
    try:
        keyword = request.args.get('keyword', type=str)
        limit = request.args.get('limit', default=20, type=int)
        
        if not keyword:
            return error_response('搜索关键词不能为空', 400)
        
        # 搜索新闻
        news_list = CCTVNewsModel.objects.search_by_keyword(keyword, limit=limit)
        
        # 转换为字典列表
        result = [news.to_dict() for news in news_list]
        
        return success_response({
            'total': len(result),
            'keyword': keyword,
            'items': result
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"搜索新闻失败: {str(e)}")
        return error_response(f'搜索新闻失败: {str(e)}', 500)