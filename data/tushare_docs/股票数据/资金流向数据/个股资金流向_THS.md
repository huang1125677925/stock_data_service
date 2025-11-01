# 个股资金流向（THS）

源链接: https://tushare.pro/document/2?doc_id=348

<!-- 以下为原始HTML内容，Markdown可直接渲染 -->

<div class="content col-md-9 col-sm-8 col-xs-12">
<div class="search-panel">
<div class="search-container">
<span class="fa fa-search search-icon"></span>
<input class="search-input" placeholder="Search" type="text"/>
</div>
</div>
<h2 id="个股资金流向（ths）">个股资金流向（THS）</h2>
<hr/>
<p>接口：moneyflow_ths<br/>描述：获取同花顺个股资金流向数据，每日盘后更新<br/>限量：单次最大6000，可根据日期或股票代码循环提取数据<br/>积分：用户需要至少5000积分才可以调取，具体请参阅<a href="https://tushare.pro/document/1?doc_id=13">积分获取办法</a> </p>
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
<td>股票代码</td>
</tr>
<tr>
<td>trade_date</td>
<td>str</td>
<td>N</td>
<td>交易日期（YYYYMMDD格式，下同）</td>
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
<td>股票代码</td>
</tr>
<tr>
<td>name</td>
<td>str</td>
<td>Y</td>
<td>股票名称</td>
</tr>
<tr>
<td>pct_change</td>
<td>float</td>
<td>Y</td>
<td>涨跌幅</td>
</tr>
<tr>
<td>latest</td>
<td>float</td>
<td>Y</td>
<td>最新价</td>
</tr>
<tr>
<td>net_amount</td>
<td>float</td>
<td>Y</td>
<td>资金净流入(万元)</td>
</tr>
<tr>
<td>net_d5_amount</td>
<td>float</td>
<td>Y</td>
<td>5日主力净额(万元)</td>
</tr>
<tr>
<td>buy_lg_amount</td>
<td>float</td>
<td>Y</td>
<td>今日大单净流入额(万元)</td>
</tr>
<tr>
<td>buy_lg_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日大单净流入占比(%)</td>
</tr>
<tr>
<td>buy_md_amount</td>
<td>float</td>
<td>Y</td>
<td>今日中单净流入额(万元)</td>
</tr>
<tr>
<td>buy_md_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日中单净流入占比(%)</td>
</tr>
<tr>
<td>buy_sm_amount</td>
<td>float</td>
<td>Y</td>
<td>今日小单净流入额(万元)</td>
</tr>
<tr>
<td>buy_sm_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日小单净流入占比(%)</td>
</tr>
</tbody></table>
<br/>
<br/>
<p><strong>接口示例</strong></p>
<pre><code class="language-python">
pro = ts.pro_api()

#获取单日全部股票数据
df = pro.moneyflow_ths(trade_date='20241011')

#获取单个股票数据
df = pro.moneyflow_ths(ts_code='002149.SZ', start_date='20241001', end_date='20241011')

</code></pre>
<pre><code>    trade_date ts_code  name  pct_change  ...  buy_md_amount  buy_md_amount_rate  buy_sm_amount  buy_sm_amount_rate
0   20241011  002149.SZ  西部材料        2.47  ...         -589.0                5.43         -191.0                1.76
1   20241010  002149.SZ  西部材料        1.22  ...        -2732.0               15.38        -1031.0                5.81
2   20241009  002149.SZ  西部材料        7.00  ...        -1941.0                9.25        -2079.0                9.90
3   20241008  002149.SZ  西部材料        5.17  ...        -2985.0                7.93        -2507.0                6.66
</code></pre>
<br/>
<br/>
</div>
