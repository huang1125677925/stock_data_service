import os
from typing import Dict, Optional, Any


def _get_tushare_token(token: Optional[str] = None) -> Optional[str]:
    """
    Resolve a Tushare token from an explicit value or environment.

    Django loads .env in settings.py, but this helper is also used by scripts
    that may import common.tushare_proxy without bootstrapping Django first.
    """
    explicit_token = token.strip() if isinstance(token, str) else token
    if explicit_token:
        return explicit_token

    env_token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if env_token:
        return env_token

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    env_token = os.environ.get("TUSHARE_TOKEN", "").strip()
    return env_token or None


def _success(data: Any, message: str = "success") -> Dict[str, Any]:
    from datetime import datetime
    return {
        "code": 200,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }


def _error(message: str, code: int = 500, **kwargs) -> Dict[str, Any]:
    from datetime import datetime
    payload = {
        "code": code,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": None,
    }
    payload.update(kwargs)
    return payload


def call_tushare(
    interface: str,
    params: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    fields: Optional[str] = None,
    use_query: bool = False,
) -> Dict[str, Any]:
    """
    调用 Tushare 接口的代理函数（供 scheduled_tasks 使用）。

    说明：为避免循环依赖，此模块放置在 common 中；外部数据获取逻辑的实际使用请在 scheduled_tasks 中进行，并将结果入库，API 只读数据库。

    Args:
        interface: 接口名称（如 'index_basic', 'anns_d', 'irm_qa_sh' 等）
        params: 传入参数字典
        token: 可选的 Tushare Token（优先使用该值，其次读取环境变量 'TUSHARE_TOKEN'）
        fields: 可选字段列表（逗号分隔字符串），传入给接口
        use_query: 是否使用 pro.query 方式调用（默认 False，优先使用属性调用）

    Returns:
        统一响应字典，包含 code/message/timestamp/data，其中 data 为 records 列表
    """
    params = params or {}

    # 延迟导入，避免未安装时影响其他模块加载
    try:
        import tushare as ts
        import pandas as pd  # noqa: F401 - 可能用于类型提示或转换
    except Exception as e:
        return _error("tushare 库未安装或导入失败", 503, error=str(e))

    # 令牌配置
    ts_token = _get_tushare_token(token)
    if ts_token:
        try:
            ts.set_token(ts_token)
        except Exception:
            # 某些环境下 set_token 可能失败，继续尝试 pro_api(token)
            pass

    try:
        pro = ts.pro_api(ts_token) if ts_token else ts.pro_api()
    except Exception as e:
        return _error("初始化 Tushare 接口失败", 500, error=str(e))

    # 构造调用
    try:
        if use_query:
            # 使用 query 统一调用
            if fields:
                params = {**params, "fields": fields}
            df = pro.query(interface, **params)
        else:
            # 使用属性接口调用
            func = getattr(pro, interface, None)
            if not callable(func):
                return _error(f"未找到接口: {interface}", 404)
            call_kwargs = dict(params)
            if fields:
                call_kwargs["fields"] = fields
            df = func(**call_kwargs)

        # 转换为 records 列表
        try:
            records = df.to_dict(orient="records")
        except Exception:
            # 处理非DataFrame返回的情况
            records = []

        return _success({
            "interface": interface,
            "count": len(records),
            "records": records,
        })

    except Exception as e:
        return _error("调用 Tushare 接口失败", 500, error=str(e), interface=interface)


def call_tushare_pro_bar(
    params: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    fields: Optional[str] = None,
) -> Dict[str, Any]:
    """
    调用 Tushare SDK 的通用行情接口 ts.pro_bar（非 pro.xxx 属性；文档注明 HTTP 暂不支持）。

    参数与官方文档一致：ts_code、asset、freq、adj、start_date、end_date、ma、factors 等。
    """
    params = dict(params or {})

    try:
        import tushare as ts
    except Exception as e:
        return _error("tushare 库未安装或导入失败", 503, error=str(e))

    ts_token = _get_tushare_token(token)
    if ts_token:
        try:
            ts.set_token(ts_token)
        except Exception:
            pass

    call_kwargs = {k: v for k, v in params.items() if v is not None and v != ""}
    if fields:
        call_kwargs["fields"] = fields

    try:
        df = ts.pro_bar(**call_kwargs)
    except Exception as e:
        return _error("调用 ts.pro_bar 失败", 500, error=str(e), interface="pro_bar")

    try:
        records = df.to_dict(orient="records")
    except Exception:
        records = []

    return _success(
        {
            "interface": "pro_bar",
            "count": len(records),
            "records": records,
        }
    )
