# -*- coding: utf-8 -*-
"""
组件：MACD XGBoost 指数增长结果邮件发送器

功能：
- 根据提供的用户名列表查询用户邮箱，使用外部传入的 HTML 内容作为邮件正文，
  并统一发送邮件到收件人列表。

参数：
- usernames(list[str] | None): 用户名列表；若为 None 则使用系统预设用户名集合。
- sender_email(str): 发件人邮箱地址；默认使用当前配置值。
- auth_code(str): QQ 邮箱 SMTP 授权码；默认使用当前配置值。
- email_html_content(str): 已生成的邮件 HTML 内容；直接作为邮件正文发送。

返回值：
- dict: {
    'emails': list[str],          # 实际发送的收件人邮箱列表
    'scanned_count': int,         # 扫描指数数量（本组件不扫描，默认 0）
    'hit_count': int,             # 命中数量（本组件不统计，默认 0）
    'send_result': dict,          # 邮件发送返回结果（含 code/message 等）
  }

事件：
- 查询用户邮箱 → 使用外部 HTML 内容 → 发送邮件。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from user_management.models import User

from common.email_utils import send_qq_email


def send_macd_xgboost_results_email(
    usernames: list[str] | None = None,
    sender_email: str = "1125677925@qq.com",
    auth_code: str = "wsxmvqhgoeszigdh",
    email_html_content: str = "",
) -> dict:
    """
    发送 MACD XGBoost 指数增长预测结果到指定用户邮箱

    功能：
    - 根据提供的用户名列表查询用户邮箱，执行指数扫描（由 `scan_func` 提供），
      生成命中结果的 HTML 邮件内容，并统一发送邮件。

    参数：
    - usernames(list[str] | None): 用户名列表；若为 None 则使用系统预设用户名集合。
    - sender_email(str): 发件人邮箱地址；默认使用当前配置值。
    - auth_code(str): QQ 邮箱 SMTP 授权码；默认使用当前配置值。
    - email_html_content(str): 已生成的邮件 HTML 内容；直接作为邮件正文发送。

    返回值：
    - dict: {
        'emails': list[str],          # 实际发送的收件人邮箱列表
        'scanned_count': int,         # 扫描指数数量
        'hit_count': int,             # 命中数量
        'send_result': dict,          # 邮件发送返回结果（含 code/message 等）
      }

    事件：
    - 查询用户邮箱 → 执行指数扫描 → 生成 HTML 邮件内容 → 发送邮件。
    """

    if not isinstance(email_html_content, str) or not email_html_content.strip():
        raise ValueError("email_html_content 不能为空，且必须为非空字符串。")

    default_user_list = [
        "admin","Neil","Eleven","huang36077","windeve","sony","jnukylin","大森不胖",
        "桐桐巴巴","LucHu","snoopy","金牛腾飞","wuxingchen","knight","tuwu","shine",
        "zxxx241","Jerome","feng","鹏鹏涨了","xiafine","heatonc","SAM","Cyt4222525","catashd"
    ]

    names = (usernames or default_user_list)
    user_email_list: list[str] = ['1605895800@qq.com', 'mymailbox_2003@163.com']
    
    for uname in names:
        if not uname or not str(uname).strip():
            continue
        user_object = User.objects.filter(username=str(uname).strip()).first()
        if user_object is None:
            print(f"用户 {uname} 不存在")
            continue
        print(f"用户 {uname} 的邮箱 {user_object.email}" )
        user_email_list.append(user_object.email)
    print(user_email_list)
    send_result = send_qq_email(
        subject=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 增长预测结果",
        body=email_html_content,
        to_emails=user_email_list,
        sender_email=sender_email,
        auth_code=auth_code,
        use_html=True,
    )

    return {
        "emails": user_email_list,
        "scanned_count": 0,
        "hit_count": 0,
        "send_result": send_result,
    }


__all__ = [
    "send_macd_xgboost_results_email",
]