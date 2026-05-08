from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .services import UserService, TokenService, InvitationCodeService
from common.response import success_response, error_response


@method_decorator(csrf_exempt, name='dispatch')
class ResetPasswordView(APIView):
    """密码重置视图"""
    authentication_classes = []
    
    def post(self, request):
        """处理密码重置请求"""
        # 获取请求数据
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        
        if not all([email, new_password]):
            return error_response("邮箱和新密码不能为空", code=400)
        
        # 调用服务层重置密码
        success, message = UserService.reset_password(email, new_password)
        
        if success:
            return success_response(message=message)
        else:
            return error_response(message, code=400)


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """用户注册视图"""
    authentication_classes = []
    
    def post(self, request):
        """处理用户注册请求"""
        # 获取请求数据
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        phone = request.data.get('phone')
        invitation_code = request.data.get('invitation_code')
        
        # 参数验证
        if not all([username, password, email]):
            return error_response("用户名、密码和邮箱不能为空", code=400)
        
        # 调用服务层进行注册
        success, message, user = UserService.register(
            username=username,
            password=password,
            email=email,
            phone=phone,
            invitation_code=invitation_code
        )
        
        if success:
            # 注册成功，返回用户信息（不包含敏感信息）
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'created_at': user.created_at
            }
            return success_response(user_data, message)
        else:
            # 注册失败，返回错误信息
            return error_response(message, code=400)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """用户登录视图"""
    authentication_classes = []
    
    def post(self, request):
        """处理用户登录请求"""
        # 获取请求数据
        username = request.data.get('username')  # 用户名或邮箱
        password = request.data.get('password')
        
        # 参数验证
        if not all([username, password]):
            return error_response("用户名和密码不能为空", code=400)
        
        # 调用服务层进行登录验证
        success, message, user, token = UserService.login(username, password)
        
        if success:
            # 登录成功，返回用户信息和令牌
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'token': token
            }
            return success_response(user_data, message)
        else:
            # 登录失败，返回错误信息，但使用200状态码
            return error_response(message, code=400)


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """用户登出视图"""
    authentication_classes = []
    
    def post(self, request):
        """处理用户登出请求"""
        token = request.headers.get('Authorization')
        if not token:
            return success_response(message='未提供令牌，跳过登出')

        if token.startswith('Bearer '):
            token = token[7:]

        success, message = UserService.logout(token)

        if success:
            return success_response(message=message)
        else:
            return error_response(message, code=400)


@method_decorator(csrf_exempt, name='dispatch')
class UserInfoView(APIView):
    """用户信息视图"""
    authentication_classes = []
    
    def get(self, request):
        """获取当前用户信息（无令牌时返回系统访客对应资料）。"""
        user = UserService.resolve_request_user(request)
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'is_admin': user.is_admin,
            'last_login': user.last_login,
            'created_at': user.created_at
        }
        return success_response(user_data)

@method_decorator(csrf_exempt, name='dispatch')
class InvitationCodeView(APIView):
    """邀请码视图"""
    authentication_classes = []
    
    def post(self, request):
        """生成邀请码"""
        user = UserService.resolve_request_user(request)
        invitation_service = InvitationCodeService()
        success, message, invitation = invitation_service.generate_invitation_code(user)

        if success:
            invitation_data = {
                'code': invitation.code,
                'expires_at': invitation.expires_at,
                'created_at': invitation.created_at
            }
            return success_response(invitation_data, message)
        else:
            return error_response(message, code=400)

    def get(self, request):
        """获取用户的邀请码列表"""
        user = UserService.resolve_request_user(request)
        invitations = InvitationCodeService.get_user_invitations(user)

        invitation_list = [{
            'id': inv.id,
            'code': inv.code,
            'is_used': inv.is_used,
            'used_by': inv.used_by.username if inv.used_by else None,
            'expires_at': inv.expires_at,
            'created_at': inv.created_at
        } for inv in invitations]

        return success_response(invitation_list)


@method_decorator(csrf_exempt, name='dispatch')
class ValidateInvitationCodeView(APIView):
    """验证邀请码视图"""
    authentication_classes = []
    
    def post(self, request):
        """验证邀请码是否有效"""
        # 获取请求数据
        code = request.data.get('code')
        
        if not code:
            return error_response("邀请码不能为空", code=400)
        
        # 验证邀请码
        success, message = InvitationCodeService.validate_code(code)
        
        if success:
            return success_response(message="邀请码有效")
        else:
            return error_response(message, code=400)
