#!/usr/bin/env python3
"""
个股数据服务
基于akshare库获取个股数据
"""

import logging
import time
import pandas as pd
import akshare as ak
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.db import transaction
from .models import IndividualStock, IndividualStockDaily, IndividualStockWeekly, IndividualStockRealtime, PerformanceReport
from common.tushare_proxy import call_tushare, call_tushare_pro_bar
from common.validators import validate_stock_symbol

logger = logging.getLogger(__name__)


class IndividualStockService:
    """个股数据服务类"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        self.request_timeout = getattr(settings, 'STOCK_REQUEST_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'STOCK_MAX_RETRIES', 3)
        
        logger.info(f"个股数据服务初始化: cache_timeout={self.cache_timeout}s")

    def _only_dict_records(self, records) -> List[Dict]:
        if not isinstance(records, list):
            return []
        return [item for item in records if isinstance(item, dict)]

    def _get_recent_open_dates(self, days: int = 15) -> List[str]:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        resp = call_tushare(
            interface='trade_cal',
            params={
                'start_date': start_date,
                'end_date': end_date,
                'is_open': '1',
            },
            fields='cal_date,is_open',
            use_query=False,
        )
        if resp.get('code') != 200:
            raise RuntimeError(resp.get('error') or resp.get('message') or '获取交易日历失败')

        return sorted(
            [
                str(item.get('cal_date'))
                for item in self._only_dict_records((resp.get('data') or {}).get('records') or [])
                if item.get('cal_date')
            ],
            reverse=True,
        )

    def _safe_float(self, value):
        if value is None or value == '':
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value):
        number = self._safe_float(value)
        return int(number) if number is not None else None

    def get_stock_list_from_tushare(self) -> Dict:
        """
        从 Tushare 获取股票列表
        功能：按最近一个有 bak_daily 数据的交易日获取全市场个股列表并映射为接口字段。
        返回值：dict，包含 trade_date 与 data。
        事件：Tushare 调用失败时抛出异常。
        """
        open_dates = self._get_recent_open_dates()
        if not open_dates:
            return {'trade_date': None, 'data': []}

        fields = (
            'trade_date,ts_code,name,pct_change,close,change,open,high,low,pre_close,'
            'vol_ratio,turn_over,swing,vol,amount,float_mv,total_mv,pe,industry,area'
        )
        for trade_date in open_dates:
            resp = call_tushare(
                interface='bak_daily',
                params={'trade_date': trade_date},
                fields=fields,
                use_query=False,
            )
            if resp.get('code') != 200:
                raise RuntimeError(resp.get('error') or resp.get('message') or '获取股票列表失败')

            records = self._only_dict_records((resp.get('data') or {}).get('records') or [])
            if not records:
                continue

            items = []
            for row in records:
                ts_code = str(row.get('ts_code') or '')
                code = ts_code.split('.')[0] if ts_code else ''
                if not code:
                    continue

                items.append({
                    'code': code,
                    'ts_code': ts_code,
                    'name': row.get('name'),
                    'industry': row.get('industry'),
                    'area': row.get('area'),
                    'dc_concept': None,
                    'index_type': None,
                    'index_type_display': None,
                    'total_shares': None,
                    'circulating_shares': None,
                    'list_date': None,
                    'pe_ratio': self._safe_float(row.get('pe')),
                    'pb_ratio': None,
                    'total_market_cap': self._safe_float(row.get('total_mv')),
                    'circulating_market_cap': self._safe_float(row.get('float_mv')),
                    'latest_price': self._safe_float(row.get('close')),
                    'change_percent': self._safe_float(row.get('pct_change')),
                    'change_amount': self._safe_float(row.get('change')),
                    'volume': self._safe_int(row.get('vol')),
                    'amount': self._safe_float(row.get('amount')),
                    'amplitude': self._safe_float(row.get('swing')),
                    'high': self._safe_float(row.get('high')),
                    'low': self._safe_float(row.get('low')),
                    'open_price': self._safe_float(row.get('open')),
                    'close_price': self._safe_float(row.get('pre_close')),
                    'volume_ratio': self._safe_float(row.get('vol_ratio')),
                    'turnover_rate': self._safe_float(row.get('turn_over')),
                    'price_change_speed': None,
                    'change_5min': None,
                    'change_60d': None,
                    'change_ytd': None,
                    'trade_date': f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}',
                    'created_at': None,
                    'updated_at': None,
                })

            return {'trade_date': f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}', 'data': items}

        return {'trade_date': None, 'data': []}
    
    def get_stock_list(self) -> Optional[List[Dict]]:
        """
        从数据库获取股票列表
        
        Returns:
            股票列表，如果数据库中没有数据则返回None
        """
        try:
            # 从数据库获取股票列表
            stocks = IndividualStock.objects.all()
            if stocks.exists():
                stock_list = [stock.to_dict() for stock in stocks]
                logger.info(f"从数据库获取{len(stock_list)}只股票信息")
                return stock_list
            else:
                logger.warning("数据库中没有股票列表数据")
                return None
            
        except Exception as e:
            logger.error(f"从数据库获取股票列表失败: {str(e)}")
            return None
    
    def get_stock_realtime(self, stock_code: str = None) -> Optional[Union[Dict, List[Dict]]]:
        """
        获取股票实时行情
        
        Args:
            stock_code: 股票代码，如果为None则获取所有股票的实时行情
        
        Returns:
            股票实时行情数据
        """
        if stock_code and not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        cache_key = f'individual_stock_realtime_{stock_code if stock_code else "all"}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code if stock_code else '所有'}实时行情")
            return cached_data
        
        try:
            # 从akshare获取实时行情
            df = ak.stock_sh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning("获取股票实时行情数据为空")
                return None
            
            # 如果指定了股票代码，则过滤数据
            if stock_code:
                df = df[df['代码'] == stock_code]
                if df.empty:
                    logger.warning(f"未找到股票{stock_code}的实时行情")
                    return None
            
            # 转换数据格式并保存到数据库
            realtime_list = []
            with transaction.atomic():
                for _, row in df.iterrows():
                    code = str(row['代码'])
                    name = str(row['名称'])
                    
                    # 获取或创建股票信息
                    stock, created = IndividualStock.objects.get_or_create(
                        code=code,
                        defaults={'name': name}
                    )
                    
                    # 更新股票信息
                    if not created:
                        stock.name = name
                        stock.pe_ratio = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None
                        stock.pb_ratio = float(row['市净率']) if pd.notna(row['市净率']) else None
                        stock.total_market_cap = float(row['总市值']) if pd.notna(row['总市值']) else None
                        stock.circulating_market_cap = float(row['流通市值']) if pd.notna(row['流通市值']) else None
                        stock.save()
                    
                    # 创建实时行情
                    realtime = IndividualStockRealtime(
                        stock=stock,
                        latest_price=float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                        change_percent=float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                        change_amount=float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                        volume=int(row['成交量']) if pd.notna(row['成交量']) else 0,
                        amount=float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                        amplitude=float(row['振幅']) if pd.notna(row['振幅']) else None,
                        high=float(row['最高']) if pd.notna(row['最高']) else None,
                        low=float(row['最低']) if pd.notna(row['最低']) else None,
                        open_price=float(row['今开']) if pd.notna(row['今开']) else None,
                        close_price=float(row['昨收']) if pd.notna(row['昨收']) else None,
                        turnover_rate=float(row['换手率']) if pd.notna(row['换手率']) else None
                    )
                    realtime.save()
                    
                    realtime_data = realtime.to_dict()
                    realtime_list.append(realtime_data)
            
            # 缓存数据
            result = realtime_list[0] if stock_code else realtime_list
            cache.set(cache_key, result, self.cache_timeout)
            
            logger.info(f"获取股票{stock_code if stock_code else '所有'}实时行情并保存到数据库")
            return result
            
        except Exception as e:
            logger.error(f"获取股票{stock_code if stock_code else '所有'}实时行情失败: {str(e)}")
            return None
    
    def get_stock_history(self, stock_code: str, start_date: str = None, end_date: str = None, adjust: str = "", frequency: str = "daily") -> Optional[List[Dict]]:
        """
        获取股票历史行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD，默认为30天前
            end_date: 结束日期，格式：YYYYMMDD，默认为今天
            adjust: 复权类型，""为不复权，"qfq"为前复权，"hfq"为后复权
            frequency: 频率，支持"daily"（默认）和"weekly"
        
        Returns:
            股票历史行情数据列表
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        # 设置默认日期
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        try:
            ts_code = self._to_ts_code(stock_code)
            freq = (frequency or "daily").lower()
            ts_freq = 'W' if freq in ("weekly", "week", "w") else 'D'
            adjust = (adjust or '').lower()

            fields = 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
            if adjust in {'qfq', 'hfq'}:
                resp = call_tushare_pro_bar(
                    params={
                        'ts_code': ts_code,
                        'asset': 'E',
                        'freq': ts_freq,
                        'adj': adjust,
                        'start_date': start_date,
                        'end_date': end_date,
                    },
                    fields=fields,
                )
            else:
                resp = call_tushare(
                    interface='weekly' if ts_freq == 'W' else 'daily',
                    params={
                        'ts_code': ts_code,
                        'start_date': start_date,
                        'end_date': end_date,
                    },
                    fields=fields,
                    use_query=False,
                )

            if resp.get('code') != 200:
                logger.warning(
                    "调用 Tushare 股票历史行情失败: stock_code=%s, code=%s, msg=%s",
                    stock_code,
                    resp.get('code'),
                    resp.get('message') or resp.get('error'),
                )
                return None

            records = self._only_dict_records((resp.get('data') or {}).get('records') or [])
            history_list = [self._normalize_tushare_history_record(row) for row in records]
            history_list = [row for row in history_list if row]
            history_list.sort(key=lambda row: row.get('date') or '')
            logger.info(f"从 Tushare 获取股票{stock_code}历史行情数据，共 {len(history_list)} 条")
            return history_list
        except Exception as e:
            logger.error(f"获取股票{stock_code}历史行情数据失败: {str(e)}")
            return None

    def _to_ts_code(self, stock_code: str) -> str:
        if '.' in stock_code:
            return stock_code.upper()
        if stock_code.startswith(('6', '9')):
            return f'{stock_code}.SH'
        if stock_code.startswith(('0', '2', '3')):
            return f'{stock_code}.SZ'
        if stock_code.startswith(('4', '8')):
            return f'{stock_code}.BJ'
        return f'{stock_code}.SZ'

    def _normalize_tushare_history_record(self, row: Dict) -> Optional[Dict]:
        raw_trade_date = str(row.get('trade_date') or '')
        if len(raw_trade_date) != 8:
            return None

        return {
            'stock_code': str(row.get('ts_code') or '').split('.')[0],
            'ts_code': row.get('ts_code'),
            'date': f'{raw_trade_date[:4]}-{raw_trade_date[4:6]}-{raw_trade_date[6:]}',
            'open_price': self._safe_float(row.get('open')),
            'close_price': self._safe_float(row.get('close')),
            'high_price': self._safe_float(row.get('high')),
            'low_price': self._safe_float(row.get('low')),
            'pre_close': self._safe_float(row.get('pre_close')),
            'change_percent': self._safe_float(row.get('pct_chg')),
            'change_amount': self._safe_float(row.get('change')),
            'volume': self._safe_int(row.get('vol')),
            'amount': self._safe_float(row.get('amount')),
            'amplitude': None,
            'turnover_rate': None,
            'created_at': None,
        }
    
    def get_stocks_history_bulk(self, stock_codes: List[str], start_date: str = None, end_date: str = None, frequency: str = "daily") -> Dict[str, List[Dict]]:
        valid_codes = [c for c in stock_codes if validate_stock_symbol(c)]
        if not valid_codes:
            return {}
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        try:
            start_date_obj = datetime.strptime(start_date, '%Y%m%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y%m%d').date()
            freq = (frequency or "daily").lower()
            Model = IndividualStockDaily
            if freq in ("weekly", "week", "w"):
                Model = IndividualStockWeekly
            qs = (
                Model.objects.select_related('stock')
                .filter(stock__code__in=valid_codes, date__gte=start_date_obj, date__lte=end_date_obj)
                .order_by('stock__code', 'date')
                .values('stock__code', 'date', 'close_price')
            )
            result: Dict[str, List[Dict]] = {code: [] for code in valid_codes}
            for row in qs:
                code = row['stock__code']
                result[code].append({
                    'date': row['date'].isoformat(),
                    'close_price': float(row['close_price']) if row['close_price'] is not None else None,
                })
            return result
        except Exception as e:
            logger.error(f"批量获取股票历史行情数据失败: {str(e)}")
            return {}
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票详细信息
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票详细信息
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        try:
            # 从数据库获取股票信息
            try:
                stock = IndividualStock.objects.get(code=stock_code)
                stock_info = stock.to_dict()
            except IndividualStock.DoesNotExist:
                logger.warning(f"未找到股票{stock_code}的信息")
                return None
            
            # 获取最新的实时行情
            try:
                realtime = IndividualStockRealtime.objects.filter(stock=stock).latest('timestamp')
                realtime_info = realtime.to_dict()
            except IndividualStockRealtime.DoesNotExist:
                logger.warning(f"未找到股票{stock_code}的实时行情数据")
                realtime_info = None
            
            # 获取最近的历史数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            history = self.get_stock_history(stock_code, start_date, end_date)
            
            # 构建详细信息
            info = {
                **stock_info,
                'realtime': realtime_info,
                'history': history[:7] if history else []
            }
            
            return info
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}详细信息失败: {str(e)}")
            return None
    
    def update_all_stocks(self) -> Tuple[int, int, int]:
        """
        更新所有股票信息和实时行情
        
        Returns:
            更新的股票数量、新增的股票数量、失败的股票数量
        """
        try:
            # 从akshare获取所有股票列表
            df = ak.stock_sh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning("获取股票列表数据为空")
                return 0, 0, 0
            
            updated_count = 0
            created_count = 0
            failed_count = 0
            
            # 更新股票信息和实时行情
            with transaction.atomic():
                for _, row in df.iterrows():
                    try:
                        code = str(row['代码'])
                        name = str(row['名称'])
                        
                        # 创建或更新股票信息
                        stock, created = IndividualStock.objects.update_or_create(
                            code=code,
                            defaults={
                                'name': name,
                                'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                                'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else None,
                                'total_market_cap': float(row['总市值']) if pd.notna(row['总市值']) else None,
                                'circulating_market_cap': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                            }
                        )
                        
                        # 创建实时行情
                        IndividualStockRealtime.objects.create(
                            stock=stock,
                            latest_price=float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                            change_percent=float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                            change_amount=float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                            volume=int(row['成交量']) if pd.notna(row['成交量']) else 0,
                            amount=float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                            amplitude=float(row['振幅']) if pd.notna(row['振幅']) else None,
                            high=float(row['最高']) if pd.notna(row['最高']) else None,
                            low=float(row['最低']) if pd.notna(row['最低']) else None,
                            open_price=float(row['今开']) if pd.notna(row['今开']) else None,
                            close_price=float(row['昨收']) if pd.notna(row['昨收']) else None,
                            turnover_rate=float(row['换手率']) if pd.notna(row['换手率']) else None
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                    except Exception as e:
                        logger.error(f"更新股票{code}信息失败: {str(e)}")
                        failed_count += 1
            
            # 清除缓存
            cache.delete('individual_stock_list')
            cache.delete('individual_stock_realtime_all')
            
            logger.info(f"更新所有股票信息完成: 更新{updated_count}只，新增{created_count}只，失败{failed_count}只")
            return updated_count, created_count, failed_count
            
        except Exception as e:
            logger.error(f"更新所有股票信息失败: {str(e)}")
            return 0, 0, 0
    
    def _get_or_create_stock(self, stock_code: str) -> Optional[IndividualStock]:
        """
        获取或创建股票信息
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票对象
        """
        try:
            # 尝试从数据库获取
            try:
                return IndividualStock.objects.get(code=stock_code)
            except IndividualStock.DoesNotExist:
                pass
            
            # 从akshare获取股票信息
            df = ak.stock_sh_a_spot_em()
            if df is None or df.empty:
                logger.warning("获取股票列表数据为空")
                return None
            
            # 过滤指定股票
            df = df[df['代码'] == stock_code]
            if df.empty:
                logger.warning(f"未找到股票{stock_code}的信息")
                return None
            
            # 创建股票信息
            row = df.iloc[0]
            stock = IndividualStock.objects.create(
                code=stock_code,
                name=str(row['名称']),
                pe_ratio=float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                pb_ratio=float(row['市净率']) if pd.notna(row['市净率']) else None,
                total_market_cap=float(row['总市值']) if pd.notna(row['总市值']) else None,
                circulating_market_cap=float(row['流通市值']) if pd.notna(row['流通市值']) else None,
            )
            
            return stock
            
        except Exception as e:
            logger.error(f"获取或创建股票{stock_code}信息失败: {str(e)}")
            return None

    def get_performance_report(self, date: str) -> Optional[List[Dict]]:
        """
        获取指定日期的业绩快报数据（仅从数据库查询）
        
        Args:
            date: 报告期，格式：YYYYMMDD，如"20200331"
            
        Returns:
            业绩快报数据列表，失败返回None
        """
        try:
            # 验证日期格式
            if not self._validate_report_date(date):
                logger.error(f"无效的报告期格式: {date}")
                return None
            
            # 先从缓存查询
            cache_key = f"performance_report_{date}"
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"从缓存获取业绩快报数据: {date}")
                return cached_data
            
            # 从数据库获取
            reports = PerformanceReport.objects.filter(report_date=date).select_related('stock')
            if reports.exists():
                report_list = [report.to_dict() for report in reports]
                cache.set(cache_key, report_list, self.cache_timeout)
                logger.info(f"从数据库获取{len(report_list)}条业绩快报数据: {date}")
                return report_list
            else:
                logger.warning(f"数据库中未找到业绩快报数据: {date}")
                return None
            
        except Exception as e:
            logger.error(f"获取业绩快报数据失败 {date}: {str(e)}")
            return None
    
    def get_stock_performance_reports(self, stock_code: str) -> Optional[List[Dict]]:
        """
        获取指定股票的所有业绩快报数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            业绩快报数据列表，失败返回None
        """
        try:
            # 验证股票代码
            if not validate_stock_symbol(stock_code):
                logger.error(f"无效的股票代码: {stock_code}")
                return None
            
            # 从数据库获取
            reports = PerformanceReport.objects.filter(
                stock__code=stock_code
            ).select_related('stock').order_by('-report_date')
            
            if reports.exists():
                report_list = [report.to_dict() for report in reports]
                logger.info(f"获取股票{stock_code}的{len(report_list)}条业绩快报数据")
                return report_list
            else:
                logger.warning(f"未找到股票{stock_code}的业绩快报数据")
                return []
            
        except Exception as e:
            logger.error(f"获取股票业绩快报数据失败 {stock_code}: {str(e)}")
            return None
    
    def _validate_report_date(self, date: str) -> bool:
        """
        验证报告期格式
        
        Args:
            date: 报告期字符串
            
        Returns:
            是否有效
        """
        if not date or len(date) != 8:
            return False
        
        try:
            year = int(date[:4])
            month_day = date[4:]
            
            # 检查年份范围
            if year < 2010 or year > datetime.now().year:
                return False
            
            # 检查月日格式
            valid_endings = ['0331', '0630', '0930', '1231']
            return month_day in valid_endings
            
        except ValueError:
            return False

class StockTagService:
    """
    股票标记服务类
    提供股票标记的查询、创建、更新、删除等功能
    支持多种标记因子的单选和多选查询
    """
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_TAG_CACHE_TIMEOUT', 300)  # 缓存5分钟
        logger.info(f"股票标记服务初始化: cache_timeout={self.cache_timeout}s")
    
    def query_stock_tags(self, **filters) -> Dict:
        """
        查询股票标记
        支持多种标记因子的单选和多选查询
        
        Args:
            **filters: 查询过滤条件
                - stock_codes: 股票代码列表
                - pattern_types: 形态类型列表
                - technical_indicator_types: 技术指标类型列表
                - stock_types: 股票类型列表
                - market_cap_types: 市值大小类型列表
                - pe_range_types: PE区间类型列表
                - pb_range_types: PB区间类型列表
                - industry_types: 行业类型列表
                - volume_types: 成交量类型列表
                - volatility_types: 波动率类型列表
                - trend_types: 趋势类型列表
                - start_date: 开始日期
                - end_date: 结束日期
                - page: 页码
                - page_size: 每页数量
        
        Returns:
            包含查询结果和分页信息的字典
        """
        from django.core.paginator import Paginator
        from django.db.models import Q
        from .models import StockTag
        
        try:
            # 构建查询条件
            query = Q()
            
            # 股票代码过滤
            stock_codes = filters.get('stock_codes')
            if stock_codes:
                query &= Q(stock__code__in=stock_codes)
            
            # 各种标记因子过滤
            pattern_types = filters.get('pattern_types')
            if pattern_types:
                query &= Q(pattern_type__in=pattern_types)
            
            technical_indicator_types = filters.get('technical_indicator_types')
            if technical_indicator_types:
                query &= Q(technical_indicator_type__in=technical_indicator_types)
            
            stock_types = filters.get('stock_types')
            if stock_types:
                query &= Q(stock_type__in=stock_types)
            
            market_cap_types = filters.get('market_cap_types')
            if market_cap_types:
                query &= Q(market_cap_type__in=market_cap_types)
            
            pe_range_types = filters.get('pe_range_types')
            if pe_range_types:
                query &= Q(pe_range_type__in=pe_range_types)
            
            pb_range_types = filters.get('pb_range_types')
            if pb_range_types:
                query &= Q(pb_range_type__in=pb_range_types)
            
            industry_types = filters.get('industry_types')
            if industry_types:
                query &= Q(industry_type__in=industry_types)
            
            volume_types = filters.get('volume_types')
            if volume_types:
                query &= Q(volume_type__in=volume_types)
            
            volatility_types = filters.get('volatility_types')
            if volatility_types:
                query &= Q(volatility_type__in=volatility_types)
            
            trend_types = filters.get('trend_types')
            if trend_types:
                query &= Q(trend_type__in=trend_types)
            
            # 日期范围过滤
            start_date = filters.get('start_date')
            if start_date:
                query &= Q(created_at__date__gte=start_date)
            
            end_date = filters.get('end_date')
            if end_date:
                query &= Q(created_at__date__lte=end_date)
            
            # 执行查询
            queryset = StockTag.objects.filter(query).select_related('stock').order_by('-created_at')
            
            # 分页处理
            page = filters.get('page', 1)
            page_size = filters.get('page_size', 20)
            
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 构建返回结果
            result = {
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'results': list(page_obj.object_list)
            }
            
            logger.info(f"查询股票标记成功，共{result['total']}条记录，当前第{page}页")
            return result
            
        except Exception as e:
            logger.error(f"查询股票标记失败: {str(e)}")
            raise
    
    def create_stock_tag(self, stock_code: str, tag_data: Dict) -> 'StockTag':
        """
        创建股票标记
        
        Args:
            stock_code: 股票代码
            tag_data: 标记数据
        
        Returns:
            创建的股票标记对象
        """
        from .models import StockTag, IndividualStock
        
        try:
            # 获取股票对象
            stock = IndividualStock.objects.get(code=stock_code)
            
            # 创建标记
            tag_data['stock'] = stock
            stock_tag = StockTag.objects.create(**tag_data)
            
            logger.info(f"创建股票{stock_code}标记成功，ID: {stock_tag.id}")
            return stock_tag
            
        except IndividualStock.DoesNotExist:
            logger.error(f"股票{stock_code}不存在")
            raise ValueError(f"股票{stock_code}不存在")
        except Exception as e:
            logger.error(f"创建股票{stock_code}标记失败: {str(e)}")
            raise
    
    def update_stock_tag(self, tag_id: int, tag_data: Dict) -> 'StockTag':
        """
        更新股票标记
        
        Args:
            tag_id: 标记ID
            tag_data: 更新的标记数据
        
        Returns:
            更新后的股票标记对象
        """
        from .models import StockTag
        
        try:
            stock_tag = StockTag.objects.get(id=tag_id)
            
            # 更新字段
            for field, value in tag_data.items():
                if hasattr(stock_tag, field):
                    setattr(stock_tag, field, value)
            
            stock_tag.save()
            
            logger.info(f"更新股票标记成功，ID: {tag_id}")
            return stock_tag
            
        except StockTag.DoesNotExist:
            logger.error(f"股票标记{tag_id}不存在")
            raise ValueError(f"股票标记{tag_id}不存在")
        except Exception as e:
            logger.error(f"更新股票标记{tag_id}失败: {str(e)}")
            raise
    
    def delete_stock_tag(self, tag_id: int) -> bool:
        """
        删除股票标记
        
        Args:
            tag_id: 标记ID
        
        Returns:
            删除是否成功
        """
        from .models import StockTag
        
        try:
            stock_tag = StockTag.objects.get(id=tag_id)
            stock_tag.delete()
            
            logger.info(f"删除股票标记成功，ID: {tag_id}")
            return True
            
        except StockTag.DoesNotExist:
            logger.error(f"股票标记{tag_id}不存在")
            raise ValueError(f"股票标记{tag_id}不存在")
        except Exception as e:
            logger.error(f"删除股票标记{tag_id}失败: {str(e)}")
            raise
    
    def get_stock_tag(self, tag_id: int) -> Optional['StockTag']:
        """
        获取单个股票标记
        
        Args:
            tag_id: 标记ID
        
        Returns:
            股票标记对象或None
        """
        from .models import StockTag
        
        try:
            stock_tag = StockTag.objects.select_related('stock').get(id=tag_id)
            logger.info(f"获取股票标记成功，ID: {tag_id}")
            return stock_tag
            
        except StockTag.DoesNotExist:
            logger.warning(f"股票标记{tag_id}不存在")
            return None
        except Exception as e:
            logger.error(f"获取股票标记{tag_id}失败: {str(e)}")
            raise
    
    def get_tag_choices(self) -> Dict:
        """
        获取所有标记因子的选择项
        
        Returns:
            包含所有标记因子选择项的字典
        """
        from .models import StockTag
        
        try:
            choices = {
                'pattern_types': StockTag.PATTERN_TYPE_CHOICES,
                'technical_indicator_types': StockTag.TECHNICAL_INDICATOR_TYPE_CHOICES,
                'stock_types': StockTag.STOCK_TYPE_CHOICES,
                'market_cap_types': StockTag.MARKET_CAP_TYPE_CHOICES,
                'pe_range_types': StockTag.PE_RANGE_TYPE_CHOICES,
                'pb_range_types': StockTag.PB_RANGE_TYPE_CHOICES,
                'industry_types': StockTag.INDUSTRY_TYPE_CHOICES,
                'volume_types': StockTag.VOLUME_TYPE_CHOICES,
                'volatility_types': StockTag.VOLATILITY_TYPE_CHOICES,
                'trend_types': StockTag.TREND_TYPE_CHOICES,
            }
            
            logger.info("获取标记因子选择项成功")
            return choices
            
        except Exception as e:
            logger.error(f"获取标记因子选择项失败: {str(e)}")
            raise
    
    def get_stock_tags_by_stock(self, stock_code: str, start_date: str = None, end_date: str = None) -> List['StockTag']:
        """
        获取指定股票的所有标记
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            股票标记列表
        """
        from django.db.models import Q
        from .models import StockTag
        
        try:
            query = Q(stock__code=stock_code)
            
            if start_date:
                query &= Q(created_at__date__gte=start_date)
            
            if end_date:
                query &= Q(created_at__date__lte=end_date)
            
            stock_tags = StockTag.objects.filter(query).select_related('stock').order_by('-created_at')
            
            logger.info(f"获取股票{stock_code}标记成功，共{len(stock_tags)}条")
            return list(stock_tags)
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}标记失败: {str(e)}")
            raise


# 创建服务实例
individual_stock_service = IndividualStockService()
stock_tag_service = StockTagService()
