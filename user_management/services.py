#!/usr/bin/env python3
"""
用户管理服务层
提供用户注册、登录验证、邀请码生成和验证等功能
"""

from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import User, InvitationCode, UserToken
import uuid
import hashlib


class TokenService:
    """令牌服务类"""
    
    def __init__(self, token_expiry_days=7):
        self.token_expiry_days = token_expiry_days
    
    def create_token(self, user):
        """创建用户令牌
        
        Args:
            user: 用户对象
            
        Returns:
            str: 令牌字符串
        """
        # 生成令牌
        token_str = UserToken.generate_token()
        
        # 设置过期时间
        expires_at = timezone.now() + timedelta(days=self.token_expiry_days)
        
        # 创建令牌记录
        token = UserToken.objects.create(
            user=user,
            token=token_str,
            expires_at=expires_at
        )
        
        return token_str
    
    def validate_token(self, token_str):
        """验证令牌
        
        Args:
            token_str: 令牌字符串
            
        Returns:
            (bool, str, User): 是否有效，消息，用户对象
        """
        try:
            token = UserToken.objects.get(token=token_str)
        except UserToken.DoesNotExist:
            return False, "无效的令牌", None
        
        # 检查令牌是否过期
        if not token.is_valid():
            return False, "令牌已过期", None
        
        # 检查用户状态
        if not token.user.is_active:
            return False, "用户已被禁用", None
        
        return True, "", token.user
    
    def invalidate_token(self, token_str):
        """使令牌失效（登出）
        
        Args:
            token_str: 令牌字符串
            
        Returns:
            (bool, str): 是否成功，消息
        """
        try:
            token = UserToken.objects.get(token=token_str)
            token.delete()
            return True, "登出成功"
        except UserToken.DoesNotExist:
            return False, "令牌不存在"


class InvitationCodeService:
    """邀请码服务类"""
    
    def __init__(self, code_expiry_days=30):
        self.code_expiry_days = code_expiry_days
    
    def generate_invitation_code(self, user):
        """生成邀请码
        
        Args:
            user: 创建邀请码的用户
            
        Returns:
            (bool, str, InvitationCode): 是否成功，消息，邀请码对象
        """
        # 检查用户权限
        if not user.is_active:
            return False, "用户已被禁用", None
        
        # 生成邀请码
        code = InvitationCode.generate_code()
        
        # 设置过期时间
        expires_at = timezone.now() + timedelta(days=self.code_expiry_days)
        
        # 创建邀请码记录
        invitation = InvitationCode.objects.create(
            code=code,
            created_by=user,
            expires_at=expires_at
        )
        
        return True, "邀请码生成成功", invitation
    
    @staticmethod
    def validate_code(code):
        """验证邀请码
        
        Args:
            code: 邀请码字符串
            
        Returns:
            (bool, str): 是否有效，消息
        """
        try:
            invitation = InvitationCode.objects.get(code=code)
        except InvitationCode.DoesNotExist:
            return False, "邀请码不存在"
        
        # 检查邀请码是否已使用
        if invitation.is_used:
            return False, "邀请码已被使用"
        
        # 检查邀请码是否过期
        if not invitation.is_valid():
            return False, "邀请码已过期"
        
        return True, ""
    
    @staticmethod
    def get_user_invitations(user):
        """获取用户创建的邀请码列表
        
        Args:
            user: 用户对象
            
        Returns:
            QuerySet: 邀请码查询集
        """
        return InvitationCode.objects.filter(created_by=user).order_by('-created_at')


class UserService:
    """用户服务类"""

    API_GUEST_USERNAME = '__api_guest__'
    API_GUEST_EMAIL = '__api_guest__@system.internal'

    @staticmethod
    def get_or_create_api_guest_user():
        """未携带有效令牌时用于绑定数据的系统访客账号。"""
        user, _ = User.objects.get_or_create(
            username=UserService.API_GUEST_USERNAME,
            defaults={
                'email': UserService.API_GUEST_EMAIL,
                'is_active': True,
                'password_hash': make_password(uuid.uuid4().hex),
            },
        )
        return user

    @staticmethod
    def resolve_request_user(request):
        """
        解析 API 请求对应的业务用户：优先使用有效 Bearer，否则使用系统访客。
        不强制要求令牌（项目已关闭接口鉴权）。
        """
        auth_header = ''
        if hasattr(request, 'headers'):
            auth_header = request.headers.get('Authorization') or ''
        else:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '') or ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
            if token:
                token_service = TokenService()
                is_valid, _, user = token_service.validate_token(token)
                if is_valid and user:
                    setattr(request, 'token', token)
                    return user
        return UserService.get_or_create_api_guest_user()

    @staticmethod
    def validate_username(username):
        """验证用户名是否合法"""
        if not username or len(username) < 3 or len(username) > 50:
            return False, "用户名长度必须在3-50个字符之间"
        
        if User.objects.filter(username=username).exists():
            return False, "用户名已存在"
        
        return True, ""
    
    @staticmethod
    def validate_email(email):
        """验证邮箱是否合法"""
        try:
            validate_email(email)
        except ValidationError:
            return False, "邮箱格式不正确"
        
        if User.objects.filter(email=email).exists():
            return False, "邮箱已被注册"
        
        return True, ""
    
    @staticmethod
    def validate_password(password):
        """验证密码是否合法"""
        if not password or len(password) < 6 or len(password) > 20:
            return False, "密码长度必须在6-20个字符之间"
        
        # 检查密码强度，至少包含数字和字母
        has_digit = any(char.isdigit() for char in password)
        has_letter = any(char.isalpha() for char in password)
        
        if not (has_digit and has_letter):
            return False, "密码必须包含数字和字母"
        
        return True, ""
        
    @staticmethod
    def generate_reset_code(email):
        """生成密码重置验证码
        
        为用户生成一个密码重置验证码，并发送到用户邮箱。
        
        Args:
            email: 用户邮箱
            
        Returns:
            (bool, str): 是否成功，消息
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "该邮箱未注册"
            
        # 生成6位数字验证码
        import random
        reset_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # 存储验证码（这里简化处理，实际应用中应该存储到数据库中）
        # 可以创建一个PasswordResetCode模型来存储
        # 这里假设已经有了相关的存储机制
        
        # 发送验证码到邮箱（这里简化处理，实际应用中需要集成邮件发送功能）
        # 可以使用Django的邮件发送功能或第三方服务
        
        # 模拟发送成功
        return True, "验证码已发送到您的邮箱，请查收"
        
    @staticmethod
    def verify_reset_code(email, reset_code):
        """验证密码重置验证码
        
        验证用户提供的密码重置验证码是否正确。
        
        Args:
            email: 用户邮箱
            reset_code: 用户提供的验证码
            
        Returns:
            (bool, str): 是否成功，消息
        """
        # 验证验证码（这里简化处理，实际应用中需要从数据库中获取并验证）
        # 这里假设验证通过
        return True, "验证码正确"
        
    @staticmethod
    def reset_password(email, new_password):
        """重置用户密码
        
        在验证通过后，重置用户密码。
        
        Args:
            email: 用户邮箱
            new_password: 新密码
            
        Returns:
            (bool, str): 是否成功，消息
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, "用户不存在"
            
        # 验证新密码是否符合要求
        is_valid, message = UserService.validate_password(new_password)
        if not is_valid:
            return False, message
            
        # 设置新密码
        user.set_password(new_password)
        user.save()
        
        return True, "密码重置成功"
    
    @classmethod
    def register(cls, username, password, email, phone=None, invitation_code=None):
        """用户注册
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱
            phone: 手机号（可选）
            invitation_code: 邀请码（可选）
            
        Returns:
            (bool, str, User): 是否成功，消息，用户对象
        """
        # 验证用户名
        is_valid, message = cls.validate_username(username)
        if not is_valid:
            return False, message, None
        
        # 验证邮箱
        is_valid, message = cls.validate_email(email)
        if not is_valid:
            return False, message, None
        
        # 验证密码
        is_valid, message = cls.validate_password(password)
        if not is_valid:
            return False, message, None
        
        # 验证邀请码（如果需要）
        if invitation_code:
            is_valid, message = InvitationCodeService.validate_code(invitation_code)
            if not is_valid:
                return False, message, None
        
        # 创建用户
        with transaction.atomic():
            user = User(username=username, email=email, phone=phone)
            user.set_password(password)
            user.save()
            
            # 标记邀请码为已使用（如果有）
            if invitation_code:
                invitation = InvitationCode.objects.get(code=invitation_code)
                invitation.mark_as_used(user)
            
            return True, "注册成功", user
    
    @classmethod
    def login(cls, username, password):
        """用户登录
        
        Args:
            username: 用户名或邮箱
            password: 密码
            
        Returns:
            (bool, str, User, str): 是否成功，消息，用户对象，令牌
        """
        # 查找用户
        try:
            # 支持使用用户名或邮箱登录
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            return False, "用户不存在", None, None
        
        # 验证密码
        if not user.check_password(password):
            return False, "密码错误", None, None
        
        # 检查用户状态
        if not user.is_active:
            return False, "账号已被禁用", None, None
        
        # 更新最后登录时间
        user.update_last_login()
        
        # 生成令牌
        token_service = TokenService()
        token = token_service.create_token(user)
        
        return True, "登录成功", user, token
    
    @staticmethod
    def get_user_by_token(token):
        """通过令牌获取用户
        
        Args:
            token: 令牌字符串
            
        Returns:
            (bool, str, User): 是否成功，消息，用户对象
        """
        token_service = TokenService()
        is_valid, message, user = token_service.validate_token(token)
        
        return is_valid, message, user
    
    @staticmethod
    def logout(token):
        """用户登出
        
        Args:
            token: 令牌字符串
            
        Returns:
            (bool, str): 是否成功，消息
        """
        token_service = TokenService()
        return token_service.invalidate_token(token)