# ETF实时日线

源链接: https://tushare.pro/document/2?doc_id=400

<!-- 以下为原始HTML内容，Markdown可直接渲染 -->

<div class="content col-md-9 col-sm-8 col-xs-12">
<div class="search-panel">
<div class="search-container">
<span class="fa fa-search search-icon"></span>
<input class="search-input" placeholder="Search" type="text"/>
</div>
</div>
<h2 id="etf实时日线">ETF实时日线</h2>
<hr/>
<p>接口：rt_etf_k<br/>描述：获取ETF实时日k线行情，支持按ETF代码或代码通配符一次性提取全部ETF实时日k线行情<br/>限量：单次最大可提取2000条数据<br/>积分：本接口是单独开权限的数据，单独申请权限请参考<a href="https://tushare.pro/document/1?doc_id=290">权限列表</a></p>
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
<td>Y</td>
<td>支持通配符方式，e.g. 5*.SH、15*.SZ、159101.SZ</td>
</tr>
<tr>
<td>topic</td>
<td>str</td>
<td>Y</td>
<td>分类参数，取上海ETF时，需要输入'HQ_FND_TICK'，参考下面例子</td>
</tr>
</tbody></table>
<br/>
注：ts_code代码一定要带<font color="red">.SH/.SZ/.BJ</font>后缀


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
<td>ts_code</td>
<td>str</td>
<td>Y</td>
<td>ETF代码</td>
</tr>
<tr>
<td>name</td>
<td>None</td>
<td>Y</td>
<td>ETF名称</td>
</tr>
<tr>
<td>pre_close</td>
<td>float</td>
<td>Y</td>
<td>昨收价</td>
</tr>
<tr>
<td>high</td>
<td>float</td>
<td>Y</td>
<td>最高价</td>
</tr>
<tr>
<td>open</td>
<td>float</td>
<td>Y</td>
<td>开盘价</td>
</tr>
<tr>
<td>low</td>
<td>float</td>
<td>Y</td>
<td>最低价</td>
</tr>
<tr>
<td>close</td>
<td>float</td>
<td>Y</td>
<td>收盘价（最新价）</td>
</tr>
<tr>
<td>vol</td>
<td>int</td>
<td>Y</td>
<td>成交量（股）</td>
</tr>
<tr>
<td>amount</td>
<td>int</td>
<td>Y</td>
<td>成交金额（元）</td>
</tr>
<tr>
<td>num</td>
<td>int</td>
<td>Y</td>
<td>开盘以来成交笔数</td>
</tr>
<tr>
<td>ask_volume1</td>
<td>int</td>
<td>N</td>
<td>委托卖盘（股）</td>
</tr>
<tr>
<td>bid_volume1</td>
<td>int</td>
<td>N</td>
<td>委托买盘（股）</td>
</tr>
</tbody></table>
<br/>
<br/>
<p><strong>接口示例</strong></p>
<pre><code class="language-python">
#获取今日开盘以来所有深市ETF实时日线和成交笔数
df = pro.rt_etf_k(ts_code='1*.SZ')

#获取今日开盘以来沪市所有ETF实时日线和成交笔数
df = pro.rt_etf_k(ts_code='5*.SH', topic='HQ_FND_TICK')

</code></pre>
<br/>
<br/>
<p><strong>数据示例</strong></p>
<pre><code>       ts_code      name      pre_close     high     open     low    close        vol     amount    num
0    520860.SH      港股通科      1.024    1.054    1.048   1.041    1.048   15071600   15780985    307
1    515320.SH    电子50        1.173    1.211    1.184   1.184    1.206    1830600    2191339     98
2    511600.SH    货币ETF     100.008  100.003  100.002  99.999  100.000      12022    1202204     28
3    501075.SH      科创主题      2.350    2.400    2.357   2.357    2.400       4200      10040     11
4    589990.SH      科创板综      1.282    1.311    1.280   1.280    1.305    4178600    5413728    147
..         ...       ...        ...      ...      ...     ...      ...        ...        ...    ...
933  516590.SH      电动汽车      1.244    1.277    1.252   1.252    1.270    1380800    1748398     79
934  502048.SH  50LOF         1.224    1.238    1.235   1.214    1.218       3200       3908      5
935  515850.SH      证券龙头      1.519    1.538    1.523   1.520    1.523   11460000   17484157    688
936  515790.SH    光伏ETF       0.912    0.929    0.919   0.910    0.923  411566128  379094370  14939
937  516190.SH    文娱ETF       1.137    1.154    1.151   1.146    1.151    1031700    1186303     87
</code></pre>
</div>
