from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Post, Comment
from django.core.paginator import Paginator
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseForbidden
from common.response import success_response, error_response
from user_management.decorators import jwt_login_required

# 帖子列表视图
@api_view(['GET'])
def post_list(request):
    """获取帖子列表"""
    posts = Post.objects.all()
    
    # 分页处理
    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(posts, per_page)
    page_obj = paginator.get_page(page_number)
    
    # 判断请求类型
    if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
        # 返回HTML页面
        return render(request, 'forum/post_list.html', {
            'posts': page_obj,
            'page': page_obj,
        })
    else:
        # 返回API响应
        data = {
            'posts': [
                {
                    'id': post.id,
                    'title': post.title,
                    'author': post.author.username,
                    'created_at': post.created_at,
                    'comment_count': post.comment_count(),
                } for post in page_obj
            ],
            'page': {
                'current': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        return success_response(data=data, message='获取帖子列表成功')

# 帖子详情视图
@api_view(['GET'])
def post_detail(request, post_id):
    """获取帖子详情"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        # 获取帖子的评论
        comments = post.comments.all()
        
        # 判断请求类型
        if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
            # 返回HTML页面
            return render(request, 'forum/post_detail.html', {
                'post': post,
                'comments': comments,
            })
        else:
            # 返回API响应
            data = {
                'post': {
                    'id': post.id,
                    'title': post.title,
                    'content': post.content,
                    'author': post.author.username,
                    'created_at': post.created_at,
                    'updated_at': post.updated_at,
                },
                'comments': [
                    {
                        'id': comment.id,
                        'content': comment.content,
                        'author': comment.author.username,
                        'created_at': comment.created_at,
                    } for comment in comments
                ]
            }
            return success_response(data=data, message='获取帖子详情成功')
    except Exception as e:
        return error_response(message='获取帖子详情失败', code=500)

# 创建帖子视图
@csrf_exempt
@api_view(['GET', 'POST'])
@jwt_login_required
@authentication_classes([])
def post_create(request):
    """创建新帖子"""
    try:
        # 处理GET请求（显示表单）
        if request.method == 'GET':
            return render(request, 'forum/post_create.html')
        
        # 处理POST请求（提交表单）
        # 获取请求数据
        if request.content_type == 'application/json':
            # API请求
            title = request.data.get('title')
            content = request.data.get('content')
        else:
            # 表单请求
            title = request.POST.get('title')
            content = request.POST.get('content')
        
        # 验证数据
        if not title or not content:
            if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
                messages.error(request, '标题和内容不能为空')
                return render(request, 'forum/post_create.html')
            else:
                return error_response(message='标题和内容不能为空', code=400)
        print(request.user)
        # 创建帖子
        post = Post.objects.create(
            title=title,
            content=content,
            author=request.user
        )
        
        # 返回成功响应
        if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
            messages.success(request, '帖子创建成功')
            return redirect('forum:post_detail', post_id=post.id)
        else:
            data = {
                'post': {
                    'id': post.id,
                    'title': post.title,
                    'content': post.content,
                    'author': post.author.username,
                    'created_at': post.created_at,
                }
            }
            return success_response(data=data, message='帖子创建成功')
    except Exception as e:
        return error_response(message='创建帖子失败 ' + str(e), code=500)

# 添加评论视图
@csrf_exempt
@api_view(['POST'])
@jwt_login_required
@authentication_classes([])
def add_comment(request, post_id):
    """添加评论"""
    try:
        # 获取帖子
        post = get_object_or_404(Post, id=post_id)
        
        # 获取请求数据
        if request.content_type == 'application/json':
            # API请求
            content = request.data.get('content')
        else:
            # 表单请求
            content = request.POST.get('content')
        
        # 验证数据
        if not content:
            if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
                messages.error(request, '评论内容不能为空')
                return redirect('forum:post_detail', post_id=post.id)
            else:
                return error_response(message='评论内容不能为空', code=400)
        
        # 创建评论
        comment = Comment.objects.create(
            post=post,
            content=content,
            author=request.user
        )
        
        # 返回成功响应
        if request.accepted_renderer.format == 'html' or 'text/html' in request.META.get('HTTP_ACCEPT', ''):
            messages.success(request, '评论添加成功')
            return redirect('forum:post_detail', post_id=post.id)
        else:
            data = {
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author': comment.author.username,
                    'created_at': comment.created_at,
                }
            }
            return success_response(data=data, message='评论添加成功')
    except Exception as e:
        return error_response(message='添加评论失败 ' + str(e), code=500)

# 删除帖子视图
@csrf_exempt
@api_view(['DELETE', 'POST'])
@jwt_login_required
@authentication_classes([])
def post_delete(request, post_id):
    """删除帖子"""
    try:
        # 获取帖子
        post = get_object_or_404(Post, id=post_id)
        
        # 检查权限（只有作者可以删除自己的帖子）
        if post.author != request.user:
            if request.accepted_renderer.format == 'html':
                messages.error(request, '您没有权限删除此帖子')
                return redirect('forum:post_detail', post_id=post.id)
            else:
                return error_response(message='您没有权限删除此帖子', code=403)
        
        # 删除帖子（这将级联删除所有相关评论）
        post.delete()
        
        # 返回成功响应
        if request.accepted_renderer.format == 'html':
            messages.success(request, '帖子删除成功')
            return redirect('forum:post_list')
        else:
            return success_response(data={'id': post_id}, message='帖子删除成功')
    except Exception as e:
        return error_response(message='删除帖子失败', code=500)
