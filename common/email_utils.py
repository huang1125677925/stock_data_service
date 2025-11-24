#!/usr/bin/env python3
"""
QQ邮箱发送工具函数

组件说明：
- 功能：提供通过 QQ 邮箱（smtp.qq.com）发送邮件的通用方法，支持纯文本/HTML正文、抄送、密送、附件。
- 参数：
  - to_emails(list[str]): 收件人邮箱列表（必填）。
  - subject(str): 邮件主题（必填）。
  - body(str): 邮件正文内容（必填）。
  - sender_email(str | None): 发件人邮箱；默认从环境变量 `QQ_EMAIL` 读取。
  - auth_code(str | None): QQ邮箱SMTP授权码；默认从环境变量 `QQ_SMTP_AUTH_CODE` 读取。
  - cc(list[str] | None): 抄送列表；默认 None。
  - bcc(list[str] | None): 密送列表；默认 None（仅参与发送，不出现在邮件头）。
  - attachments(list[str] | None): 文件路径列表；默认 None。
  - use_html(bool): 正文是否为 HTML 格式；默认 False。

- 返回值：
  - dict: 标准结构体，包含 `code/message/data` 字段；成功时 code=200，失败时 code=500。

- 事件：
  - 构建 MIME 消息（文本/HTML、附件、抄送/密送）。
  - 通过 SMTP SSL 连接 `smtp.qq.com:465` 登录并发送邮件。
  - 返回统一结构的成功或错误数据。
"""

import os
import smtplib
import ssl
import mimetypes
from typing import List, Optional, Dict, Any
from datetime import datetime

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate


def _result_success(data: Any, message: str = "邮件发送成功") -> Dict[str, Any]:
    return {
        "code": 200,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }


def _result_error(message: str, code: int = 500, **kwargs) -> Dict[str, Any]:
    payload = {
        "code": code,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": None,
    }
    payload.update(kwargs)
    return payload


def send_qq_email(
    to_emails: List[str],
    subject: str,
    body: str,
    sender_email: Optional[str] = None,
    auth_code: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    use_html: bool = False,
) -> Dict[str, Any]:
    """
    使用 QQ 邮箱发送邮件

    功能：
    - 通过 QQ SMTP 服务（smtp.qq.com:465）发送邮件，支持文本/HTML正文、抄送/密送与附件。

    参数：
    - to_emails(list[str]): 收件人列表。
    - subject(str): 邮件主题。
    - body(str): 邮件正文。
    - sender_email(str | None): 发件人邮箱；缺省从环境变量 `QQ_EMAIL` 读取。
    - auth_code(str | None): QQ邮箱SMTP授权码；缺省从环境变量 `QQ_SMTP_AUTH_CODE` 读取。
    - cc(list[str] | None): 抄送列表。
    - bcc(list[str] | None): 密送列表（不出现在邮件头）。
    - attachments(list[str] | None): 附件文件路径列表。
    - use_html(bool): 正文是否为 HTML 格式。

    返回值：
    - dict: { code, message, timestamp, data }
      data 包含：from/to/cc/subject/sent_at/attachment_count。

    事件：
    - 构造 MIME 邮件 → 连接 SMTP SSL → 登录 → 发送 → 关闭连接。
    """
    try:
        if not to_emails:
            return _result_error("收件人列表不能为空", 400)

        sender = sender_email or os.environ.get("QQ_EMAIL")
        password = auth_code or os.environ.get("QQ_SMTP_AUTH_CODE")
        if not sender or not password:
            return _result_error("未配置发件人邮箱或授权码（QQ_EMAIL/QQ_SMTP_AUTH_CODE）", 400)

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(to_emails)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = subject

        if use_html:
            msg.attach(MIMEText(body, "html", "utf-8"))
        else:
            msg.attach(MIMEText(body, "plain", "utf-8"))

        attach_count = 0
        if attachments:
            for path in attachments:
                try:
                    ctype, encoding = mimetypes.guess_type(path)
                    main_type, sub_type = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
                    with open(path, "rb") as f:
                        part = MIMEApplication(f.read(), _subtype=sub_type)
                    filename = os.path.basename(path)
                    part.add_header("Content-Disposition", "attachment", filename=filename)
                    msg.attach(part)
                    attach_count += 1
                except Exception as e:
                    return _result_error(f"附件添加失败: {path} - {e}")

        recipients = list(to_emails)
        if cc:
            recipients.extend(cc)
        if bcc:
            recipients.extend(bcc)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as server:
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())

        return _result_success({
            "from": sender,
            "to": to_emails,
            "cc": cc or [],
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "attachment_count": attach_count,
        })
    except smtplib.SMTPAuthenticationError as e:
        return _result_error("SMTP认证失败，请检查授权码", 401, error=str(e))
    except smtplib.SMTPException as e:
        return _result_error("SMTP发送失败", 500, error=str(e))
    except Exception as e:
        return _result_error("邮件发送异常", 500, error=str(e))