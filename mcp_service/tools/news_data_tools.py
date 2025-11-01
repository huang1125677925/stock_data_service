"""
新闻数据工具模块

提供新闻快讯、上市公司公告、新闻联播、新闻通讯、上证E互动等数据接口工具。
所有接口都通过 scheduled_tasks 中的 Tushare 代理来获取数据，遵循架构规范。
"""

from __future__ import annotations
from typing import Dict, Optional
from mcp.server.fastmcp import FastMCP
from common.response import success_response, error_response


def register_news_data_tools(mcp: FastMCP) -> None:
    """
    注册新闻数据相关的工具函数
    
    包含以下接口：
    1. news - 新闻快讯
    2. anns_d - 上市公司公告
    3. cctv_news - 新闻联播文字稿
    4. major_news - 新闻通讯
    5. irm_qa_sh - 上证E互动问答
    """

    def _call_tushare_proxy(interface: str, params: Optional[Dict] = None, 
                           fields: Optional[str] = None, token: Optional[str] = None) -> Dict:
        """调用通用 Tushare 代理（common模块），集中外部访问逻辑"""
        try:
            from common.tushare_proxy import call_tushare
            return call_tushare(interface=interface, params=params or {}, 
                              token=token, fields=fields, use_query=False)
        except Exception as e:
            return error_response(f"调用 Tushare 代理失败: {str(e)}")

    @mcp.tool()
    def get_news_flash(
        src: str,
        start_date: str,
        end_date: str,
        token: Optional[str] = None
    ) -> Dict:
        """
        获取新闻快讯数据
        
        接口：news
        描述：获取主流新闻网站的快讯新闻数据，提供超过6年以上历史新闻
        限量：单次最大1500条新闻，可根据时间参数循环提取历史
        
        参数说明：
        - src (str, 必选): 新闻来源，支持以下值：
          * 'sina' - 新浪财经，获取新浪财经实时资讯
          * 'wallstreetcn' - 华尔街见闻快讯
          * '10jqka' - 同花顺财经新闻
          * 'eastmoney' - 东方财富财经新闻
          * 'yuncaijing' - 云财经新闻
          * 'fenghuang' - 凤凰新闻
          * 'jinrongjie' - 金融界新闻
          * 'cls' - 财联社快讯
          * 'yicai' - 第一财经快讯
        - start_date (str, 必选): 开始日期，格式：'2018-11-20 09:00:00'
        - end_date (str, 必选): 结束日期，格式：'2018-11-20 22:05:03'
        - token (str, 可选): Tushare API token
        
        返回数据字段：
        - datetime: 新闻时间
        - content: 内容
        - title: 标题
        - channels: 分类（默认不显示）
        """
        params = {
            'src': src,
            'start_date': start_date,
            'end_date': end_date
        }
        return _call_tushare_proxy('news', params, token=token)

    @mcp.tool()
    def get_company_announcements(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict:
        """
        获取上市公司全量公告数据
        
        接口：anns_d
        描述：获取全量公告数据，提供pdf下载URL
        限量：单次最大2000条数据，可以根据日期循环获取全量
        权限：本接口为单独权限
        
        参数说明：
        - ts_code (str, 可选): 股票代码，如 '000001.SZ'
        - ann_date (str, 可选): 公告日期，格式：'20230621' (yyyymmdd)
        - start_date (str, 可选): 公告开始日期，格式：'20230601' (yyyymmdd)
        - end_date (str, 可选): 公告结束日期，格式：'20230630' (yyyymmdd)
        - token (str, 可选): Tushare API token
        
        返回数据字段：
        - ann_date: 公告日期
        - ts_code: 股票代码
        - name: 股票名称
        - title: 标题
        - url: URL，原文下载链接
        - rec_time: 发布时间（默认不显示）
        """
        params = {}
        if ts_code:
            params['ts_code'] = ts_code
        if ann_date:
            params['ann_date'] = ann_date
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
            
        return _call_tushare_proxy('anns_d', params, token=token)

    @mcp.tool()
    def get_cctv_news(
        date: str,
        token: Optional[str] = None
    ) -> Dict:
        """
        获取新闻联播文字稿数据
        
        接口：cctv_news
        描述：获取新闻联播文字稿数据，数据开始于2006年6月，超过12年历史
        限量：可根据日期参数循环提取，总量不限制
        权限：本接口需单独开权限
        
        参数说明：
        - date (str, 必选): 日期，格式：'20181211' (YYYYMMDD)
        - token (str, 可选): Tushare API token
        
        返回数据字段：
        - date: 日期
        - title: 标题
        - content: 内容
        
        注意：新闻联播进行了分段处理，每一个大段都加了标题处理，便于选择和过滤
        """
        params = {'date': date}
        return _call_tushare_proxy('cctv_news', params, token=token)

    @mcp.tool()
    def get_major_news(
        src: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_content: bool = False,
        token: Optional[str] = None
    ) -> Dict:
        """
        获取新闻通讯（长篇）数据
        
        接口：major_news
        描述：获取长篇通讯信息，覆盖主要新闻资讯网站，提供超过8年历史新闻
        限量：单次最大400行记录，可循环提取保存到本地
        权限：本接口需单独开权限
        
        参数说明：
        - src (str, 可选): 新闻来源，支持：新华网、凤凰财经、同花顺、新浪财经、华尔街见闻、中证网、财新网、第一财经、财联社
        - start_date (str, 可选): 新闻发布开始时间，格式：'2018-11-21 00:00:00'
        - end_date (str, 可选): 新闻发布结束时间，格式：'2018-11-22 00:00:00'
        - include_content (bool, 可选): 是否包含新闻内容，默认False（内容字段默认不显示，需要在fields里指定）
        - token (str, 可选): Tushare API token
        
        返回数据字段：
        - title: 标题
        - content: 内容（仅当include_content=True时返回）
        - pub_time: 发布时间
        - src: 来源网站
        """
        params = {}
        if src:
            params['src'] = src
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
            
        fields = None
        if include_content:
            fields = 'title,content,pub_time,src'
            
        return _call_tushare_proxy('major_news', params, fields=fields, token=token)

    @mcp.tool()
    def get_shanghai_interactive_qa(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        pub_date_start: Optional[str] = None,
        pub_date_end: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict:
        """
        获取上证E互动问答数据
        
        接口：irm_qa_sh
        描述：获取上交所e互动董秘问答文本数据，历史数据开始于2023年6月
        上证e互动是由上海证券交易所建立的沟通平台，旨在引导和促进上市公司、投资者等各市场参与主体之间的信息沟通
        限量：单次请求最大返回3000行数据，可根据股票代码，日期等参数循环提取全部数据
        权限：用户后120积分可以试用，正式权限为10000积分
        
        参数说明：
        - ts_code (str, 可选): 股票代码，如 '600519.SH'
        - trade_date (str, 可选): 交易日期，格式：'20250212' (YYYYMMDD)
        - start_date (str, 可选): 开始日期，格式：'20250201' (YYYYMMDD)
        - end_date (str, 可选): 结束日期，格式：'20250228' (YYYYMMDD)
        - pub_date_start (str, 可选): 发布开始日期，格式：'2025-06-03 16:43:03'
        - pub_date_end (str, 可选): 发布结束日期，格式：'2025-06-03 18:43:23'
        - token (str, 可选): Tushare API token
        
        返回数据字段：
        - ts_code: 股票代码
        - name: 公司名称
        - trade_date: 日期
        - q: 问题
        - a: 回复
        - pub_time: 回复时间
        """
        params = {}
        if ts_code:
            params['ts_code'] = ts_code
        if trade_date:
            params['trade_date'] = trade_date
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if pub_date_start:
            params['pub_date'] = pub_date_start
        if pub_date_end:
            params['pub_date'] = pub_date_end
            
        return _call_tushare_proxy('irm_qa_sh', params, token=token)

    @mcp.tool()
    def get_shenzhen_interactive_qa(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        pub_date_start: Optional[str] = None,
        pub_date_end: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict:
        """
        获取深证互动易问答数据
        
        接口：irm_qa_sz
        描述：获取深交所互动易董秘问答文本数据
        深证互动易是深圳证券交易所建立的投资者与上市公司沟通平台
        限量：单次请求最大返回3000行数据，可根据股票代码，日期等参数循环提取全部数据
        
        参数说明：
        - ts_code (str, 可选): 股票代码，如 '000001.SZ'
        - trade_date (str, 可选): 交易日期，格式：'20250212' (YYYYMMDD)
        - start_date (str, 可选): 开始日期，格式：'20250201' (YYYYMMDD)
        - end_date (str, 可选): 结束日期，格式：'20250228' (YYYYMMDD)
        - pub_date_start (str, 可选): 发布开始日期，格式：'2025-06-03 16:43:03'
        - pub_date_end (str, 可选): 发布结束日期，格式：'2025-06-03 18:43:23'
        - token (str, 可选): Tushare API token
        
        返回数据字段：
        - ts_code: 股票代码
        - name: 公司名称
        - trade_date: 日期
        - q: 问题
        - a: 回复
        - pub_time: 回复时间
        """
        params = {}
        if ts_code:
            params['ts_code'] = ts_code
        if trade_date:
            params['trade_date'] = trade_date
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if pub_date_start:
            params['pub_date'] = pub_date_start
        if pub_date_end:
            params['pub_date'] = pub_date_end
            
        return _call_tushare_proxy('irm_qa_sz', params, token=token)