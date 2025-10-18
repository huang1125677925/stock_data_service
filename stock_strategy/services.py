import pandas as pd
import numpy as np
import pywencai
from datetime import datetime, timedelta
from .models import IndexRPS
from .stock_screening_strategy import StockScreeningStrategy
from indival_stock_data.models import IndividualStock

class RPSService:
    """指数RPS强度排名服务"""
    
    @staticmethod
    def get_date_range(days):
        """计算日期范围"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
    
    @staticmethod
    def calculate_rps(df, change_col):
        """计算RPS值
        RPS = (1 - 排名 / 总板块数) × 100
        """
        # 转换涨跌幅为数值
        df[change_col] = pd.to_numeric(df[change_col].astype(str).str.replace('%', ''), errors='coerce')
        # 计算排名（按涨跌幅降序排列）
        df['rank'] = df[change_col].rank(ascending=False, method='min')
        # 计算RPS
        total_count = len(df)
        df['RPS'] = ((1 - df['rank'] / total_count) * 100).round(2)
        # 删除临时列
        df.drop('rank', axis=1, inplace=True)
        return df
    
    @staticmethod
    def get_index_data(period):
        """获取指数数据"""
        start_date, end_date = RPSService.get_date_range(period)
        query = f"指数代码886开头，近{period}日涨跌幅"
        try:
            # 使用pywencai获取数据
            df = pywencai.get(query=query, query_type='zhishu')
            # 检查返回数据
            if df.empty:
                return None, f"未获取到近{period}日数据"
            
            # 查找涨跌幅列
            change_col = None
            for col in df.columns:
                if "区间涨跌幅" in col:
                    change_col = col
                    break
            if not change_col:
                return None, f"未找到近{period}日涨跌幅列"
            
            # 查找代码列
            code_cols = [col for col in df.columns if "指数代码" in col]
            if not code_cols:
                return None, f"未找到近{period}日代码列"
            code_col = code_cols[0]
            
            # 查找名称列
            name_cols = [col for col in df.columns if "指数简称" in col]
            if not name_cols:
                return None, f"未找到近{period}日名称列"
            name_col = name_cols[0]
            
            # 提取关键列
            result_df = df[[code_col, name_col, change_col]].copy()
            result_df.columns = ['指数代码', '指数简称', f'{period}日涨跌幅']
            
            # 计算RPS
            result_df = RPSService.calculate_rps(result_df, f'{period}日涨跌幅')
            result_df.rename(columns={'RPS': f'RPS_{period}'}, inplace=True)
            
            return result_df, None
        except Exception as e:
            return None, f"获取近{period}日数据失败: {str(e)}"
    
    @staticmethod
    def get_rps_data(periods):
        """获取多个周期的RPS数据"""
        dataframes = {}
        errors = []
        
        for period in periods:
            df, error = RPSService.get_index_data(period)
            if df is not None:
                dataframes[period] = df
            else:
                errors.append(error)
        
        if not dataframes:
            return None, errors
        
        # 合并数据
        merged_df = None
        for i, period in enumerate(periods):
            if period not in dataframes:
                continue
                
            if i == 0 or merged_df is None:
                merged_df = dataframes[period]
            else:
                merged_df = pd.merge(
                    merged_df,
                    dataframes[period],
                    on=['指数代码', '指数简称'],
                    how='outer'
                )
        
        # 排序
        if merged_df is not None:
            merged_df = merged_df.sort_values(by=[f'RPS_{p}' for p in periods if p in dataframes], ascending=False)
        
        return merged_df, errors
    
    @staticmethod
    def save_rps_data(df, periods):
        """保存RPS数据到数据库"""
        saved_count = 0
        for _, row in df.iterrows():
            for period in periods:
                if f'RPS_{period}' not in df.columns or f'{period}日涨跌幅' not in df.columns:
                    continue
                    
                rps_value = row[f'RPS_{period}']
                change_percent = row[f'{period}日涨跌幅']
                
                if pd.isna(rps_value) or pd.isna(change_percent):
                    continue
                    
                IndexRPS.objects.create(
                    index_code=row['指数代码'],
                    index_name=row['指数简称'],
                    period=period,
                    change_percent=change_percent,
                    rps_value=rps_value
                )
                saved_count += 1
        
        return saved_count


class StockScreeningService:
    """
    股票筛选服务类
    
    功能：提供股票筛选相关的业务逻辑服务
    包含前高突破策略的应用和结果处理
    
    事件：
    - screen_stocks: 执行股票筛选
    - get_screening_history: 获取筛选历史
    - export_results: 导出筛选结果
    """
    
    def __init__(self):
        """初始化服务"""
        pass
    
    def screen_stocks_by_previous_high(self, window_size: int = 20, 
                                     volume_multiplier: float = 1.5,
                                     stock_codes: list = None,
                                     limit: int = 50) -> dict:
        """
        使用前高突破策略筛选股票
        
        Args:
            window_size: 分析窗口大小（交易日数量）
            volume_multiplier: 成交量放大倍数
            stock_codes: 指定股票代码列表，为None时筛选所有股票
            limit: 返回结果数量限制
            
        Returns:
            包含筛选结果和统计信息的字典
        """
        try:
            # 创建策略实例
            strategy = StockScreeningStrategy(
                window_size=window_size,
                volume_multiplier=volume_multiplier
            )
            
            # 执行筛选
            candidates = strategy.get_top_candidates(
                stock_codes=stock_codes,
                limit=limit
            )
            
            # 统计信息
            total_analyzed = IndividualStock.objects.count() if not stock_codes else len(stock_codes)
            found_count = len(candidates)
            
            return {
                'success': True,
                'data': {
                    'candidates': candidates,
                    'statistics': {
                        'total_analyzed': total_analyzed,
                        'found_count': found_count,
                        'success_rate': round(found_count / total_analyzed * 100, 2) if total_analyzed > 0 else 0,
                        'window_size': window_size,
                        'volume_multiplier': volume_multiplier,
                        'analysis_time': datetime.now().isoformat()
                    }
                },
                'message': f'成功筛选出 {found_count} 只符合条件的股票'
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'股票筛选失败: {str(e)}'
            }
    
    def get_stock_analysis_detail(self, stock_code: str, window_size: int = 20,
                                volume_multiplier: float = 1.5) -> dict:
        """
        获取单只股票的详细分析结果
        
        Args:
            stock_code: 股票代码
            window_size: 分析窗口大小
            volume_multiplier: 成交量放大倍数
            
        Returns:
            股票详细分析结果
        """
        try:
            stock = IndividualStock.objects.get(code=stock_code)
            strategy = StockScreeningStrategy(
                window_size=window_size,
                volume_multiplier=volume_multiplier
            )
            
            analysis_result = strategy.analyze_single_stock(stock)
            
            if analysis_result:
                # 获取更多详细信息
                trading_data = strategy.get_recent_trading_data(stock, window_size)
                
                return {
                    'success': True,
                    'data': {
                        'analysis_result': analysis_result,
                        'trading_data': [
                            {
                                'date': data.date.isoformat(),
                                'open_price': float(data.open_price),
                                'close_price': float(data.close_price),
                                'high_price': float(data.high_price),
                                'low_price': float(data.low_price),
                                'volume': data.volume,
                                'amount': float(data.amount),
                                'change_percent': float(data.change_percent)
                            }
                            for data in trading_data
                        ]
                    },
                    'message': '获取股票分析详情成功'
                }
            else:
                return {
                    'success': False,
                    'data': None,
                    'message': '该股票不符合筛选条件'
                }
                
        except IndividualStock.DoesNotExist:
            return {
                'success': False,
                'data': None,
                'message': f'股票代码 {stock_code} 不存在'
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'获取股票分析详情失败: {str(e)}'
            }
    
    def validate_parameters(self, window_size: int, volume_multiplier: float) -> dict:
        """
        验证策略参数
        
        Args:
            window_size: 窗口大小
            volume_multiplier: 成交量倍数
            
        Returns:
            验证结果
        """
        errors = []
        
        if not isinstance(window_size, int) or window_size < 5 or window_size > 100:
            errors.append('窗口大小必须是5-100之间的整数')
        
        if not isinstance(volume_multiplier, (int, float)) or volume_multiplier < 1.0 or volume_multiplier > 10.0:
            errors.append('成交量倍数必须是1.0-10.0之间的数值')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

rps_service = RPSService()