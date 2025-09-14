from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    # 帖子列表
    path('posts/', views.post_list, name='post_list'),
    # 帖子详情
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    # 创建帖子
    path('posts/create/', views.post_create, name='post_create'),
    # 删除帖子
    path('posts/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    # 添加评论
    path('posts/<int:post_id>/comment/', views.add_comment, name='add_comment'),
]