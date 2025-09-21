#!/usr/bin/env python3
"""
股票数据模型类
用于表示从baostock等数据源获取的结构化数据
"""
from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal
from datetime import date


@dataclass
class StockDailyData:
    """
    股票日频数据类
    用于表示从baostock获取的日频K线数据
    对应查询参数：date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST
    
    属性说明：
    - date: 交易日期（格式：YYYY-MM-DD）
    - code: 证券代码（格式：sh.600000）
    - open: 开盘价
    - high: 最高价
    - low: 最低价
    - close: 收盘价
    - preclose: 前收盘价
    - volume: 成交量（单位：股）
    - amount: 成交额（单位：元）
    - adjustflag: 复权状态(1：后复权， 2：前复权，3：不复权）
    - turn: 换手率
    - tradestatus: 交易状态(1：正常交易 0：停牌）
    - pctChg: 涨跌幅（百分比）
    - isST: 是否ST股，1是，0否
    """
    date: str
    code: str
    open: float
    high: float
    low: float
    close: float
    preclose: float
    volume: int
    amount: float
    adjustflag: str
    turn: Optional[float] = None
    tradestatus: Optional[str] = None
    pctChg: Optional[float] = None
    isST: Optional[str] = None
    
    @classmethod
    def from_baostock_row(cls, row_data: List[str]) -> 'StockDailyData':
        """
        从baostock返回的行数据创建StockDailyData实例
        
        :param row_data: baostock查询返回的行数据列表
        :return: StockDailyData实例
        """
        # 确保数据长度正确
        if len(row_data) < 14:
            raise ValueError(f"数据格式不正确，期望至少14个字段，实际获得{len(row_data)}个字段")
            
        # 转换数据类型
        return cls(
            date=row_data[0],
            code=row_data[1],
            open=float(row_data[2]) if row_data[2] else 0.0,
            high=float(row_data[3]) if row_data[3] else 0.0,
            low=float(row_data[4]) if row_data[4] else 0.0,
            close=float(row_data[5]) if row_data[5] else 0.0,
            preclose=float(row_data[6]) if row_data[6] else 0.0,
            volume=int(float(row_data[7])) if row_data[7] else 0,
            amount=float(row_data[8]) if row_data[8] else 0.0,
            adjustflag=row_data[9],
            turn=float(row_data[10]) if row_data[10] else None,
            tradestatus=row_data[11],
            pctChg=float(row_data[12]) if row_data[12] else None,
            isST=row_data[13]
        )
    
    def to_dict(self) -> dict:
        """
        将数据转换为字典格式
        
        :return: 字典格式的数据
        """
        return {
            'date': self.date,
            'code': self.code,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'preclose': self.preclose,
            'volume': self.volume,
            'amount': self.amount,
            'adjustflag': self.adjustflag,
            'turn': self.turn,
            'tradestatus': self.tradestatus,
            'pctChg': self.pctChg,
            'isST': self.isST
        }
    
    def to_model_dict(self) -> dict:
        """
        将数据转换为适合IndividualStockDaily模型的字典格式
        
        :return: 适合IndividualStockDaily模型的字典格式
        """
        return {
            'open_price': self.open,
            'high_price': self.high,
            'low_price': self.low,
            'close_price': self.close,
            'volume': self.volume,
            'amount': self.amount,
            'change_percent': self.pctChg if self.pctChg is not None else 0.0,
            'change_amount': self.close - self.preclose if self.close and self.preclose else 0.0,
            'amplitude': (self.high - self.low) / self.low if self.high and self.low else 0.0,
            'turnover_rate': self.turn
        }