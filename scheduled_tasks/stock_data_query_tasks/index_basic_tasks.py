import sys
import os
from pathlib import Path
import django

# 初始化Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
from typing import Optional

from django.db import transaction
from stock_market.models import IndexBasicData
from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)


def sync_index_basic(market: Optional[str] = 'SW') -> dict:
    """
    同步Tushare指数基本信息到数据库（仅保存ts_code与name字段）。

    说明：外部数据获取通过 common.tushare_proxy 完成，任务逻辑位于 scheduled_tasks；
    API 层仅从数据库读取，符合架构规范。

    参数：
        market (str): 市场代码，默认'SW'（申万指数）。可选：SSE、SZSE、CSI、MSCI等。

    返回：
        dict: {'status': 'success'|'warning'|'error', 'created': int, 'updated': int, 'skipped': int}
    """
    logger.info(f"开始同步 Tushare 指数基础信息, market={market}")

    try:
        # 调用tushare接口
        params = {}
        if market:
            params['market'] = market
        resp = call_tushare('index_basic', params=params, use_query=False)

        if resp.get('code') != 200:
            logger.error(f"调用Tushare失败: {resp.get('message')} | {resp.get('error')}")
            return {"status": "error", "message": resp.get('message') or 'Tushare调用失败'}

        records = (resp.get('data') or {}).get('records') or []
        if not records:
            logger.warning("Tushare返回空记录")
            return {"status": "warning", "message": "Tushare返回空记录", "created": 0, "updated": 0, "skipped": 0}

        existing = {code: name for code, name in IndexBasicData.objects.values_list('code', 'name')}
        created_count = 0
        updated_count = 0
        skipped_count = 0

        to_create = []
        to_update = []

        for item in records:
            ts_code = item.get('ts_code')
            name = item.get('name')
            if not ts_code or not name:
                skipped_count += 1
                continue

            if ts_code in existing:
                # 名称变化则更新
                if existing[ts_code] != name:
                    to_update.append((ts_code, name))
                else:
                    skipped_count += 1
            else:
                to_create.append(IndexBasicData(code=ts_code, name=name))

        # 批量写入
        if to_create:
            with transaction.atomic():
                IndexBasicData.objects.bulk_create(to_create, batch_size=500)
                created_count = len(to_create)

        if to_update:
            for code, name in to_update:
                with transaction.atomic():
                    IndexBasicData.objects.filter(code=code).update(name=name)
                    updated_count += 1

        logger.info(f"指数基础信息同步完成: created={created_count}, updated={updated_count}, skipped={skipped_count}")
        return {"status": "success", "created": created_count, "updated": updated_count, "skipped": skipped_count}

    except Exception as e:
        logger.error(f"指数基础信息同步失败: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == '__main__':
    # 允许本文件直接运行以调试同步逻辑
    result = sync_index_basic(market='SW')
    print(result)