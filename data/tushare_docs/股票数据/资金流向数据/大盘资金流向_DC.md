# 大盘资金流向（DC）

源链接: https://tushare.pro/document/2?doc_id=345

<!-- 以下为原始HTML内容，Markdown可直接渲染 -->

<div class="content col-md-9 col-sm-8 col-xs-12">
<div class="search-panel">
<div class="search-container">
<span class="fa fa-search search-icon"></span>
<input class="search-input" placeholder="Search" type="text"/>
</div>
</div>
<h2 id="大盘资金流向（dc）">大盘资金流向（DC）</h2>
<hr/>
<p>接口：moneyflow_mkt_dc<br/>描述：获取东方财富大盘资金流向数据，每日盘后更新<br/>限量：单次最大3000条，可根据日期或日期区间循环获取<br/>积分：120积分可试用，5000积分可正式调取，具体请参阅<a href="https://tushare.pro/document/1?doc_id=13">积分获取办法</a> </p>
<br/>
<br/>
**输入参数**

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
<td>trade_date</td>
<td>str</td>
<td>N</td>
<td>交易日期(YYYYMMDD格式，下同）</td>
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
<td>close_sh</td>
<td>float</td>
<td>Y</td>
<td>上证收盘价（点）</td>
</tr>
<tr>
<td>pct_change_sh</td>
<td>float</td>
<td>Y</td>
<td>上证涨跌幅(%)</td>
</tr>
<tr>
<td>close_sz</td>
<td>float</td>
<td>Y</td>
<td>深证收盘价（点）</td>
</tr>
<tr>
<td>pct_change_sz</td>
<td>float</td>
<td>Y</td>
<td>深证涨跌幅(%)</td>
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
</tbody></table>
<br/>
<br/>
<p><strong>接口示例</strong></p>
<pre><code class="language-python">
#获取当日所有板块资金流向
df = pro.moneyflow_mkt_dc(start_date='20240901', end_date='20240930')
</code></pre>
<br/>
<br/>
<p><strong>数据示例</strong></p>
<pre><code>     trade_date close_sh ptc_change_sh  close_sz pct_change_sz   buy_elg_amount    buy_lg_amount
0    20240930  3336.50          8.06  10529.76         10.67   -6500884480.00  -29199228928.00
1    20240927  3087.53          2.89   9514.86          6.71   17175101440.00   -3564773376.00
2    20240926  3000.95          3.61   8916.65          4.44   18894807552.00   -2446319616.00
3    20240925  2896.31          1.16   8537.73          1.21   -4010342144.00  -10390331392.00
4    20240924  2863.13          4.15   8435.70          4.36   22524846080.00    5433212928.00
5    20240923  2748.92          0.44   8083.38          0.10    -926530816.00   -5776028928.00
6    20240920  2736.81          0.03   8075.14         -0.15   -4991644160.00   -6899648256.00
7    20240919  2736.02          0.69   8087.60          1.19    3472006400.00    1882220032.00
8    20240918  2717.28          0.49   7992.25          0.11   -5056087040.00   -7836610048.00
9    20240913  2704.09         -0.48   7983.55         -0.88   -5527845376.00   -9092720640.00
10   20240912  2717.12         -0.17   8054.24         -0.63   -3747197184.00   -5645509632.00
11   20240911  2721.80         -0.82   8105.38          0.39   -3585276416.00   -6461025792.00
12   20240910  2744.19          0.28   8073.83          0.13   -2726709504.00   -3818158336.00
13   20240909  2736.49         -1.06   8063.27         -0.83   -7874987776.00   -8608827904.00
14   20240906  2765.81         -0.81   8130.77         -1.44   -5892936960.00  -13908542976.00
15   20240905  2788.31          0.14   8249.66          0.28    1211718400.00   -3910650112.00
16   20240904  2784.28         -0.67   8226.24         -0.51   -7008298240.00  -11212970496.00
17   20240903  2802.98         -0.29   8268.05          1.17     263304192.00   -3680828928.00
18   20240902  2811.04         -1.10   8172.21         -2.11  -18689678336.00  -20967354368.00
</code></pre>
</div>
