# 股票历史数据获取工具

## 功能简介
使用Akshare接口获取沪深京A股的历史交易数据，并将数据保存为CSV文件。

## 文件说明

### 1. get_stock_history.py
主脚本文件，包含以下功能：
- 获取指定股票的历史交易数据
- 将数据列名转换为标准格式：trade_date, open, high, low, close, vol
- 自动保存为CSV文件，文件名以股票代码命名

#### 使用方法
```bash
python get_stock_history.py
```
默认获取平安银行(000001)最近一年的数据。

也可以修改main函数中的symbol变量来获取其他股票数据：
```python
def main():
    symbol = "600519"  # 贵州茅台
    # ... 其余代码不变
```

### 2. stock_data_cli.py
命令行工具，支持灵活的参数配置。

#### 使用方法
```bash
# 基本用法
python stock_data_cli.py 股票代码

# 指定日期范围
python stock_data_cli.py 000001 --start 20240101 --end 20240331

# 使用前复权数据
python stock_data_cli.py 000001 --adjust qfq

# 指定输出目录
python stock_data_cli.py 000001 --output ./my_data
```

#### 参数说明
- `symbol`: 必填参数，股票代码（如000001）
- `--start, -s`: 开始日期，格式YYYYMMDD，默认为一年前
- `--end, -e`: 结束日期，格式YYYYMMDD，默认为今天
- `--adjust, -a`: 复权方式，可选值：''(不复权)、'qfq'(前复权)、'hfq'(后复权)
- `--output, -o`: 输出目录，默认为'data'

## 数据格式
生成的CSV文件包含以下列：
- trade_date: 交易日期 (YYYY-MM-DD格式)
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- vol: 成交量（单位：手）

## 示例

### 获取贵州茅台2024年第一季度数据
```bash
python stock_data_cli.py 600519 --start 20240101 --end 20240331
```

### 获取平安银行前复权数据
```bash
python stock_data_cli.py 000001 --adjust qfq
```

## 注意事项
1. 确保已安装akshare库：`pip install akshare`
2. 获取的数据为沪深京A股数据
3. 当日收盘价请在收盘后获取
4. 数据按日频率更新