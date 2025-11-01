导入tushare

import tushare as ts
这里注意， tushare版本需大于1.2.10

设置token

ts.set_token('your token here')
以上方法只需要在第一次或者token失效后调用，完成调取tushare数据凭证的设置，正常情况下不需要重复设置。也可以忽略此步骤，直接用pro_api('your token')完成初始化

初始化pro接口

pro = ts.pro_api()
如果上一步骤ts.set_token('your token')无效或不想保存token到本地，也可以在初始化接口里直接设置token:

pro = ts.pro_api('your token')
数据调取

以获取交易日历信息为例：

df = pro.trade_cal(exchange='', start_date='20180901', end_date='20181001', fields='exchange,cal_date,is_open,pretrade_date', is_open='0')
或者

df = pro.query('trade_cal', exchange='', start_date='20180901', end_date='20181001', fields='exchange,cal_date,is_open,pretrade_date', is_open='0')
调取结果：

    exchange  cal_date    is_open pretrade_date
0          SSE       20180901        0      20180831
1          SSE       20180902        0      20180831
2          SSE       20180908        0      20180907
3          SSE       20180909        0      20180907
4          SSE       20180915        0      20180914
5          SSE       20180916        0      20180914
6          SSE       20180922        0      20180921
7          SSE       20180923        0      20180921
8          SSE       20180924        0      20180921
9          SSE       20180929        0      20180928
10         SSE       20180930        0      20180928
11         SSE       20181001        0      20180928