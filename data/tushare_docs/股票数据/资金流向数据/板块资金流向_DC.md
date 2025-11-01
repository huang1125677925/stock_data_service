# 东财概念及行业板块资金流向（DC）

源链接: https://tushare.pro/document/2?doc_id=344

<!-- 以下为原始HTML内容，Markdown可直接渲染 -->

<div class="content col-md-9 col-sm-8 col-xs-12">
<div class="search-panel">
<div class="search-container">
<span class="fa fa-search search-icon"></span>
<input class="search-input" placeholder="Search" type="text"/>
</div>
</div>
<h2 id="东财概念及行业板块资金流向（dc）">东财概念及行业板块资金流向（DC）</h2>
<hr/>
<p>接口：moneyflow_ind_dc<br/>描述：获取东方财富板块资金流向，每天盘后更新<br/>限量：单次最大可调取5000条数据，可以根据日期和代码循环提取全部数据<br/>积分：5000积分可以调取，具体请参阅<a href="https://tushare.pro/document/1?doc_id=13">积分获取办法</a> </p>
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
<tr>
<td>content_type</td>
<td>str</td>
<td>N</td>
<td>资金类型(行业、概念、地域)</td>
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
<td>content_type</td>
<td>str</td>
<td>Y</td>
<td>数据类型</td>
</tr>
<tr>
<td>ts_code</td>
<td>str</td>
<td>Y</td>
<td>DC板块代码（行业、概念、地域）</td>
</tr>
<tr>
<td>name</td>
<td>str</td>
<td>Y</td>
<td>板块名称</td>
</tr>
<tr>
<td>pct_change</td>
<td>float</td>
<td>Y</td>
<td>板块涨跌幅（%）</td>
</tr>
<tr>
<td>close</td>
<td>float</td>
<td>Y</td>
<td>板块最新指数</td>
</tr>
<tr>
<td>net_amount</td>
<td>float</td>
<td>Y</td>
<td>今日主力净流入 净额（元）</td>
</tr>
<tr>
<td>net_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日主力净流入净占比%</td>
</tr>
<tr>
<td>buy_elg_amount</td>
<td>float</td>
<td>Y</td>
<td>今日超大单净流入 净额（元）</td>
</tr>
<tr>
<td>buy_elg_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日超大单净流入 净占比%</td>
</tr>
<tr>
<td>buy_lg_amount</td>
<td>float</td>
<td>Y</td>
<td>今日大单净流入 净额（元）</td>
</tr>
<tr>
<td>buy_lg_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日大单净流入 净占比%</td>
</tr>
<tr>
<td>buy_md_amount</td>
<td>float</td>
<td>Y</td>
<td>今日中单净流入 净额（元）</td>
</tr>
<tr>
<td>buy_md_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日中单净流入 净占比%</td>
</tr>
<tr>
<td>buy_sm_amount</td>
<td>float</td>
<td>Y</td>
<td>今日小单净流入 净额（元）</td>
</tr>
<tr>
<td>buy_sm_amount_rate</td>
<td>float</td>
<td>Y</td>
<td>今日小单净流入 净占比%</td>
</tr>
<tr>
<td>buy_sm_amount_stock</td>
<td>str</td>
<td>Y</td>
<td>今日主力净流入最大股</td>
</tr>
<tr>
<td>rank</td>
<td>int</td>
<td>Y</td>
<td>序号</td>
</tr>
</tbody></table>
<br/>
<br/>
<p><strong>接口示例</strong></p>
<pre><code class="language-python">
#获取当日所有板块资金流向
df = pro.moneyflow_ind_dc(trade_date='20240927', fields='trade_date,name,pct_change, close, net_amount,net_amount_rate,rank')
</code></pre>
<br/>
<br/>
<p><strong>数据示例</strong></p>
<pre><code>     trade_date   name    pct_change      close      net_amount net_amount_rate  rank
0    20240927  互联网服务       6.28   16883.55   3056382208.00            3.93     1
1    20240927     证券       8.23  135249.80   2875528704.00            4.64     2
2    20240927   软件开发       8.28     721.35   2733378816.00            3.18     3
3    20240927   酿酒行业       6.47   49330.63   2568183040.00            5.24     4
4    20240927     电池       8.37     731.85   1328346624.00            3.05     5
..        ...    ...        ...        ...             ...             ...   ...
81   20240927   石油行业       2.31    4654.40   -611530368.00           -9.39    82
82   20240927   汽车整车       4.05    1386.22   -629528064.00           -2.42    83
83   20240927   综合行业       3.06    7437.08   -667341600.00           -7.28    84
84   20240927   家电行业       3.95   15815.68   -670035968.00           -2.37    85
85   20240927     银行      -0.33    3401.83  -2340180224.00           -6.41    86
</code></pre>
</div>
