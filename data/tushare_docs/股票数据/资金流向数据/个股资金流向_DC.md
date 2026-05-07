# 个股资金流向（DC）

源链接: https://tushare.pro/document/2?doc_id=349

<!-- 以下为原始HTML内容，Markdown可直接渲染 -->

<div class="content col-md-9 col-sm-8 col-xs-12">
<div class="search-panel">
<div class="search-container">
<span class="fa fa-search search-icon"></span>
<input class="search-input" placeholder="Search" type="text"/>
</div>
</div>
<h2 id="个股资金流向（dc）">个股资金流向（DC）</h2>
<hr/>
<p>接口：moneyflow_dc<br/>描述：获取东方财富个股资金流向数据，每日盘后更新，数据开始于20230911<br/>限量：单次最大获取6000条数据，可根据日期或股票代码循环提取数据<br/>积分：用户需要至少5000积分才可以调取，具体请参阅<a href="https://tushare.pro/document/1?doc_id=13">积分获取办法</a> </p>
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
<td>close</td>
<td>float</td>
<td>Y</td>
<td>最新价</td>
</tr>
<tr>
<td>net_amount</td>
<td>float</td>
<td>Y</td>
<td>今日主力净流入额（万元）</td>
</tr>
<tr>
<td>net_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日主力净流入净占比（%）</td>
</tr>
<tr>
<td>buy_elg_amount</td>
<td>float</td>
<td>Y</td>
<td>今日超大单净流入额（万元）</td>
</tr>
<tr>
<td>buy_elg_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日超大单净流入占比（%）</td>
</tr>
<tr>
<td>buy_lg_amount</td>
<td>float</td>
<td>Y</td>
<td>今日大单净流入额（万元）</td>
</tr>
<tr>
<td>buy_lg_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日大单净流入占比（%）</td>
</tr>
<tr>
<td>buy_md_amount</td>
<td>float</td>
<td>Y</td>
<td>今日中单净流入额（万元）</td>
</tr>
<tr>
<td>buy_md_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日中单净流入占比（%）</td>
</tr>
<tr>
<td>buy_sm_amount</td>
<td>float</td>
<td>Y</td>
<td>今日小单净流入额（万元）</td>
</tr>
<tr>
<td>buy_sm_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日小单净流入占比（%）</td>
</tr>
</tbody></table>
<br/>
<br/>
<p><strong>接口示例</strong></p>
<pre><code class="language-python">
pro = ts.pro_api()

#获取单日全部股票数据
df = pro.moneyflow_dc(trade_date='20241011')

#获取单个股票数据
df = pro.moneyflow_dc(ts_code='002149.SZ', start_date='20240901', end_date='20240913')

</code></pre>
<br/>
<br/>
<pre><code>    trade_date ts_code  name  pct_change  ...  buy_md_amount  buy_md_amount_rate  buy_sm_amount  buy_sm_amount_rate
0   20240913  002149.SZ  西部材料       -1.34  ...         -12.65               -0.35         -62.43               -1.72
1   20240912  002149.SZ  西部材料        1.43  ...          13.71                0.33        -388.43               -9.25
2   20240911  002149.SZ  西部材料       -0.79  ...         -26.10               -1.68          95.69                6.15
3   20240910  002149.SZ  西部材料       -0.08  ...        -199.50               -7.26         -69.29               -2.52
4   20240909  002149.SZ  西部材料        1.12  ...          66.76                2.48        -198.12               -7.37
5   20240906  002149.SZ  西部材料       -2.49  ...        -104.57               -2.74         769.65               20.19
6   20240905  002149.SZ  西部材料       -0.70  ...        -307.62               -8.11         346.51                9.14
7   20240904  002149.SZ  西部材料       -0.92  ...         370.98                9.56         -23.25               -0.60
8   20240903  002149.SZ  西部材料        0.93  ...        -195.45               -3.87         643.41               12.75
9   20240902  002149.SZ  西部材料       -3.44  ...         195.50                2.32         988.69               11.71
</code></pre>
</div>
