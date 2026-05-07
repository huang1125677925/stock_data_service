# 同花顺行业资金流向（THS）

源链接: https://tushare.pro/document/2?doc_id=343

<!-- 以下为原始HTML内容，Markdown可直接渲染 -->

<div class="content col-md-9 col-sm-8 col-xs-12">
<div class="search-panel">
<div class="search-container">
<span class="fa fa-search search-icon"></span>
<input class="search-input" placeholder="Search" type="text"/>
</div>
</div>
<h2 id="同花顺行业资金流向（ths）">同花顺行业资金流向（THS）</h2>
<hr/>
<p>接口：moneyflow_ind_ths<br/>描述：获取同花顺行业资金流向，每日盘后更新<br/>限量：单次最大可调取5000条数据，可以根据日期和代码循环提取全部数据<br/>积分：5000积分可以调取，具体请参阅<a href="https://tushare.pro/document/1?doc_id=13">积分获取办法</a> </p>
<br/>
<br/>
<p><strong>输入参数</strong></p>
<table>
<thead>
<tr>
<th>名称</th>
<th>类型</th>
<th>必选</th>
<th>描述</th>
</tr>
</thead>
<tbody><tr>
<td>ts_code</td>
<td>str</td>
<td>N</td>
<td>代码</td>
</tr>
<tr>
<td>trade_date</td>
<td>str</td>
<td>N</td>
<td>交易日期(YYYYMMDD格式，下同)</td>
</tr>
<tr>
<td>start_date</td>
<td>str</td>
<td>N</td>
<td>开始日期</td>
</tr>
<tr>
<td>end_date</td>
<td>str</td>
<td>N</td>
<td>结束日期</td>
</tr>
</tbody></table>
<br/>
<br/>
<p><strong>输出参数</strong></p>
<table>
<thead>
<tr>
<th>名称</th>
<th>类型</th>
<th>默认显示</th>
<th>描述</th>
</tr>
</thead>
<tbody><tr>
<td>trade_date</td>
<td>str</td>
<td>Y</td>
<td>交易日期</td>
</tr>
<tr>
<td>ts_code</td>
<td>str</td>
<td>Y</td>
<td>板块代码</td>
</tr>
<tr>
<td>industry</td>
<td>str</td>
<td>Y</td>
<td>板块名称</td>
</tr>
<tr>
<td>lead_stock</td>
<td>str</td>
<td>Y</td>
<td>领涨股票名称</td>
</tr>
<tr>
<td>close</td>
<td>float</td>
<td>Y</td>
<td>收盘指数</td>
</tr>
<tr>
<td>pct_change</td>
<td>float</td>
<td>Y</td>
<td>指数涨跌幅</td>
</tr>
<tr>
<td>company_num</td>
<td>int</td>
<td>Y</td>
<td>公司数量</td>
</tr>
<tr>
<td>pct_change_stock</td>
<td>float</td>
<td>Y</td>
<td>领涨股涨跌幅</td>
</tr>
<tr>
<td>close_price</td>
<td>float</td>
<td>Y</td>
<td>领涨股最新价</td>
</tr>
<tr>
<td>net_buy_amount</td>
<td>float</td>
<td>Y</td>
<td>流入资金(亿元)</td>
</tr>
<tr>
<td>net_sell_amount</td>
<td>float</td>
<td>Y</td>
<td>流出资金(亿元)</td>
</tr>
<tr>
<td>net_amount</td>
<td>float</td>
<td>Y</td>
<td>净额(亿元)</td>
</tr>
</tbody></table>
<br/>
<br/>
<p><strong>接口示例</strong></p>
<pre><code class="language-python">
#获取当日所有同花顺行业资金流向
df = pro.moneyflow_ind_ths(trade_date='20240927')
</code></pre>
<br/>
<br/>
<p><strong>数据示例</strong></p>
<pre><code>  trade_date   ts_code industry     close  company_num net_buy_amount net_sell_amount net_amount
0    20240927  881267.TI     能源金属  15021.70           16         490.00           46.00       3.00
1    20240927  881273.TI       白酒   3251.85           20        1890.00          179.00      10.00
2    20240927  881279.TI     光伏设备   5940.19           70        1120.00           94.00      17.00
3    20240927  881157.TI       证券   1407.41           50        3680.00          319.00      49.00
4    20240927  877137.TI     软件开发   1375.49          137        2260.00          204.00      22.00
..        ...        ...      ...       ...          ...            ...             ...        ...
85   20240927  881148.TI     港口航运    901.87           37         190.00           20.00      -1.00
86   20240927  881105.TI   煤炭开采加工   2271.57           34         220.00           26.00      -4.00
87   20240927  881169.TI      贵金属   2141.46           12         240.00           32.00      -8.00
88   20240927  881149.TI   公路铁路运输   1224.59           31         210.00           29.00      -7.00
89   20240927  877035.TI       银行   1080.14           84        1190.00          159.00     -40.00

[90 rows x 8 columns]
</code></pre>
</div>
