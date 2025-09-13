import pandas as pd
import numpy as np
import pywencai
from datetime import datetime, timedelta
from .models import IndexRPS

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

rps_service = RPSService()