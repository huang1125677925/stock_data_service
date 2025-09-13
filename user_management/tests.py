#!/usr/bin/env python3
"""
用户管理应用测试
"""

from django.test import TestCase, Client
from django.urls import reverse
from .models import User, InvitationCode, UserToken
from .services import UserService, TokenService, InvitationCodeService
import json
from rest_framework.test import APIClient


class UserManagementTestCase(TestCase):
    """
    用户管理应用测试用例
    """
    
    def setUp(self):
        """
        测试前准备
        """
        # 创建测试用户
        self.user_service = UserService()
        self.token_service = TokenService()
        self.invitation_service = InvitationCodeService()
        
        # 创建管理员用户
        self.admin = User.objects.create(
            username='admin_test',
            email='admin@example.com',
            is_admin=True
        )
        self.admin.set_password('Admin123456')
        self.admin.save()
        
        # 创建普通用户
        self.user = User.objects.create(
            username='user_test',
            email='user@example.com'
        )
        self.user.set_password('User123456')
        self.user.save()
        
        # 创建邀请码
        _, _, self.invitation_code = self.invitation_service.generate_invitation_code(self.admin)
        
        # 创建客户端
        self.client = APIClient()
    
    def test_register(self):
        """
        测试用户注册
        """
        # 注册数据
        data = {
            'username': 'new_user',
            'password': 'NewUser123456',
            'email': 'new_user@example.com',
            'invitation_code': self.invitation_code.code
        }
        
        # 发送请求
        response = self.client.post(
            reverse('user_register'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['code'], 200)
        self.assertEqual(response_data['message'], '注册成功')
        
        # 验证用户是否创建成功
        user = User.objects.filter(username='new_user').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'new_user@example.com')
        
        # 验证邀请码是否已使用
        invitation_code = InvitationCode.objects.get(code=self.invitation_code.code)
        self.assertTrue(invitation_code.is_used)
        self.assertEqual(invitation_code.used_by, user)
    
    def test_login(self):
        """
        测试用户登录
        """
        # 登录数据
        data = {
            'username': 'user_test',
            'password': 'User123456'
        }
        
        # 发送请求
        response = self.client.post(
            reverse('user_login'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['code'], 200)
        self.assertEqual(response_data['message'], '登录成功')
        
        # 验证令牌是否创建成功
        token = response_data['data']['token']
        self.assertIsNotNone(token)
        
        # 验证令牌是否有效
        is_valid, _, user = self.token_service.validate_token(token)
        self.assertTrue(is_valid)
        self.assertEqual(user.id, self.user.id)
    
    def test_logout(self):
        """
        测试用户登出
        """
        # 先登录获取令牌
        token = self.token_service.create_token(self.user)
        
        # 发送请求
        response = self.client.post(
            reverse('user_logout'),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['code'], 200)
        self.assertEqual(response_data['message'], '登出成功')
        
        # 验证令牌是否已失效
        is_valid, _, _ = self.token_service.validate_token(token)
        self.assertFalse(is_valid)
    
    def test_user_info(self):
        """
        测试获取用户信息
        """
        # 先登录获取令牌
        token = self.token_service.create_token(self.user)
        
        # 发送请求
        response = self.client.get(
            reverse('user_info'),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['code'], 200)
        self.assertEqual(response_data['data']['username'], self.user.username)
        self.assertEqual(response_data['data']['email'], self.user.email)
    
    def test_invitation_code(self):
        """
        测试生成邀请码
        """
        # 先登录获取令牌
        token = self.token_service.create_token(self.admin)
        
        # 发送请求
        response = self.client.post(
            reverse('invitation_code'),
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['code'], 200)
        self.assertEqual(response_data['message'], '邀请码生成成功')
        
        # 验证邀请码是否创建成功
        code = response_data['data']['code']
        invitation_code = InvitationCode.objects.filter(code=code).first()
        self.assertIsNotNone(invitation_code)
        self.assertEqual(invitation_code.created_by, self.admin)
    
    def test_validate_invitation_code(self):
        """
        测试验证邀请码
        """
        # 验证数据
        data = {
            'code': self.invitation_code.code
        }
        
        # 发送请求
        response = self.client.post(
            reverse('validate_invitation_code'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['code'], 200)
        self.assertEqual(response_data['message'], '邀请码有效')
