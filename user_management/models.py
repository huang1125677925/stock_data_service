from django.db import models
import uuid
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import F
from django.contrib.auth.hashers import make_password, check_password


class User(models.Model):
    """用户模型"""
    username = models.CharField(max_length=50, unique=True, verbose_name='用户名')
    password_hash = models.CharField(max_length=128, verbose_name='密码哈希')
    email = models.EmailField(unique=True, verbose_name='邮箱')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    is_admin = models.BooleanField(default=False, verbose_name='是否管理员')
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='最后登录时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """设置密码，自动进行哈希处理"""
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        """验证密码"""
        return check_password(raw_password, self.password_hash)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])


class InvitationCode(models.Model):
    """邀请码模型"""
    code = models.CharField(max_length=20, unique=True, verbose_name='邀请码')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_invitations', null=True, blank=True, verbose_name='创建者')
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_invitation', verbose_name='使用者')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '邀请码'
        verbose_name_plural = '邀请码'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.code
    
    @classmethod
    def generate_code(cls):
        """生成唯一邀请码"""
        return str(uuid.uuid4()).replace('-', '')[:12].upper()
    
    def is_valid(self):
        """检查邀请码是否有效"""
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self, user):
        """标记邀请码为已使用"""
        self.is_used = True
        self.used_by = user
        self.save(update_fields=['is_used', 'used_by'])


class UserToken(models.Model):
    """用户令牌模型，用于身份验证"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens', verbose_name='用户')
    token = models.CharField(max_length=64, unique=True, verbose_name='令牌')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '用户令牌'
        verbose_name_plural = '用户令牌'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}的令牌"
    
    @classmethod
    def generate_token(cls):
        """生成唯一令牌"""
        return str(uuid.uuid4()).replace('-', '')
    
    def is_valid(self):
        """检查令牌是否有效"""
        return self.expires_at > timezone.now()


class SiteVisitCounter(models.Model):
    """站点访问计数器"""
    key = models.CharField(max_length=50, unique=True, default='site_total', verbose_name='计数键')
    total_count = models.PositiveBigIntegerField(default=0, verbose_name='总访问数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '站点访问计数'
        verbose_name_plural = '站点访问计数'
        ordering = ['key']

    def __str__(self):
        return f'{self.key}: {self.total_count}'

    @classmethod
    def increment_total(cls):
        """原子递增站点总访问数并返回最新值。"""
        try:
            counter, _ = cls.objects.get_or_create(
                key='site_total',
                defaults={'total_count': 0},
            )
        except IntegrityError:
            counter = cls.objects.get(key='site_total')

        cls.objects.filter(pk=counter.pk).update(
            total_count=F('total_count') + 1,
            updated_at=timezone.now(),
        )
        counter.refresh_from_db(fields=['total_count', 'updated_at'])
        return counter.total_count
