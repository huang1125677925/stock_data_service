from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Post, Comment
import json
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

class ForumTestCase(TestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # 创建测试帖子
        self.post = Post.objects.create(
            title='测试帖子',
            content='这是一个测试帖子的内容',
            author=self.user
        )
        
        # 创建测试评论
        self.comment = Comment.objects.create(
            post=self.post,
            content='这是一个测试评论',
            author=self.user
        )
        
        # 创建测试客户端
        self.client = Client()
        
        # 创建API测试客户端
        self.api_client = APIClient()
        
        # 获取用户令牌
        refresh = RefreshToken.for_user(self.user)
        self.auth_token = str(refresh.access_token)
        
        # 设置认证头
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.auth_token}')
    
    def test_post_list(self):
        """测试帖子列表功能"""
        # 测试API响应
        response = self.client.get(reverse('forum:post_list'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('posts', data)
        self.assertEqual(len(data['posts']), 1)
        
        # 测试HTML响应
        response = self.client.get(reverse('forum:post_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forum/post_list.html')
    
    def test_post_detail(self):
        """测试帖子详情功能"""
        # 测试API响应
        response = self.client.get(
            reverse('forum:post_detail', args=[self.post.id]),
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('post', data)
        self.assertIn('comments', data)
        
        # 测试HTML响应
        response = self.client.get(reverse('forum:post_detail', args=[self.post.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forum/post_detail.html')
    
    def test_post_create(self):
        """测试创建帖子功能"""
        # 登录
        self.client.login(username='testuser', password='testpassword')
        
        # 测试GET请求（获取表单页面）
        response = self.client.get(reverse('forum:post_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'forum/post_create.html')
        
        # 测试API创建帖子
        post_data = {
            'title': '新测试帖子',
            'content': '这是一个通过API创建的测试帖子'
        }
        response = self.client.post(
            reverse('forum:post_create'),
            data=json.dumps(post_data),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # 测试表单创建帖子
        post_data = {
            'title': '另一个测试帖子',
            'content': '这是一个通过表单创建的测试帖子'
        }
        response = self.client.post(reverse('forum:post_create'), post_data)
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证帖子是否创建成功
        self.assertEqual(Post.objects.count(), 3)  # 初始帖子 + 两个新创建的帖子
    
    def test_add_comment(self):
        """测试添加评论功能"""
        # 登录
        self.client.login(username='testuser', password='testpassword')
        
        # 测试API添加评论
        comment_data = {
            'content': '这是一个通过API添加的测试评论'
        }
        response = self.client.post(
            reverse('forum:add_comment', args=[self.post.id]),
            data=json.dumps(comment_data),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # 测试表单添加评论
        comment_data = {
            'content': '这是一个通过表单添加的测试评论'
        }
        response = self.client.post(
            reverse('forum:add_comment', args=[self.post.id]),
            comment_data
        )
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证评论是否添加成功
        self.assertEqual(Comment.objects.count(), 3)  # 初始评论 + 两个新添加的评论
    
    def test_post_delete(self):
        """测试删除帖子功能"""
        # 登录
        self.client.login(username='testuser', password='testpassword')
        
        # 创建一个新帖子用于测试删除
        post_to_delete = Post.objects.create(
            title='待删除的帖子',
            content='这个帖子将被删除',
            author=self.user
        )
        
        # 测试API删除帖子
        response = self.client.delete(
            reverse('forum:post_delete', args=[post_to_delete.id]),
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 验证帖子是否删除成功
        with self.assertRaises(Post.DoesNotExist):
            Post.objects.get(id=post_to_delete.id)
        
        # 创建另一个帖子用于测试表单删除
        post_to_delete = Post.objects.create(
            title='待删除的帖子2',
            content='这个帖子将通过表单删除',
            author=self.user
        )
        
        # 测试表单删除帖子
        response = self.client.post(reverse('forum:post_delete', args=[post_to_delete.id]))
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证帖子是否删除成功
        with self.assertRaises(Post.DoesNotExist):
            Post.objects.get(id=post_to_delete.id)
    
    def test_permission_checks(self):
        """测试权限检查"""
        # 创建另一个用户
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword'
        )
        
        # 创建一个由other_user发布的帖子
        other_post = Post.objects.create(
            title='其他用户的帖子',
            content='这是由其他用户发布的帖子',
            author=other_user
        )
        
        # 登录测试用户
        self.client.login(username='testuser', password='testpassword')
        
        # 尝试删除其他用户的帖子（API）
        response = self.client.delete(
            reverse('forum:post_delete', args=[other_post.id]),
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(response.status_code, 403)  # 禁止访问
        
        # 尝试删除其他用户的帖子（表单）
        response = self.client.post(reverse('forum:post_delete', args=[other_post.id]))
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证帖子是否仍然存在
        self.assertTrue(Post.objects.filter(id=other_post.id).exists())
