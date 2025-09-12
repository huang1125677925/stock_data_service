# -*- coding: utf-8 -*-
import pymysql
from datetime import datetime
import sys
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import os
from contextlib import contextmanager


class DatabaseConfig:
    """数据库配置类"""
    MYSQL_CONFIG = {
        'host': os.environ.get('DB_HOST', '47.120.53.64'),
        'user': os.environ.get('DB_USER', 'hc'),
        'password': os.environ.get('DB_PASSWORD', '1125677925'),
        'database': os.environ.get('DB_NAME', 'stock_db'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }


class DatabaseManager:
    """数据库连接管理器"""
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.connection = None
            cls._instance.connect()
        return cls._instance
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(**DatabaseConfig.MYSQL_CONFIG)
        except Exception as e:
            logging.error(f"数据库连接失败: {e}")
            sys.exit(1)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not self.connection or not self.connection.open:
            self.connect()
        try:
            yield self.connection
        except Exception as e:
            logging.error(f"数据库操作失败: {e}")
            raise
    
    def execute(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> pymysql.cursors.Cursor:
        """执行SQL语句"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    return cursor
        except Exception as e:
            logging.error(f"执行SQL失败: {sql}, 参数: {params}, 错误: {e}")
            if self.connection and self.connection.open:
                self.connection.rollback()
            raise

    def query(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> List[Dict[str, Any]]:
        """查询数据"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
        except Exception as e:
            logging.error(f"查询失败: {sql}, 参数: {params}, 错误: {e}")
            return []

    def query_one(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> Optional[Dict[str, Any]]:
        """查询单条数据"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchone()
        except Exception as e:
            logging.error(f"查询单条数据失败: {sql}, 参数: {params}, 错误: {e}")
            return None

    def insert(self, sql: str, params: Union[tuple, dict]) -> int:
        """插入数据"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logging.error(f"插入数据失败: {sql}, 参数: {params}, 错误: {e}")
            if self.connection and self.connection.open:
                self.connection.rollback()
            raise

    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection and self.connection.open:
            self.connection.close()


class ModelBase:
    """模型基类，提供类似Django ORM的基础功能"""
    # 表名，子类需要覆盖
    table_name = None
    # 字段定义，子类需要覆盖
    fields = []
    # 主键字段，默认为id
    primary_key = 'id'
    
    def __init__(self, **kwargs):
        self._data = {}
        self._dirty = set()  # 跟踪已修改的字段
        
        # 设置初始值
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # 标记为未修改状态
        self._dirty.clear()
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            # 如果值发生变化，标记为已修改
            if name not in self._data or self._data.get(name) != value:
                self._dirty.add(name)
            self._data[name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._data.copy()
    
    def is_dirty(self) -> bool:
        """检查对象是否被修改"""
        return len(self._dirty) > 0
    
    def get_dirty_fields(self) -> Dict[str, Any]:
        """获取已修改的字段"""
        return {k: self._data[k] for k in self._dirty if k in self._data}
    
    def refresh_from_db(self) -> None:
        """从数据库刷新对象数据"""
        if hasattr(self, self.primary_key) and getattr(self, self.primary_key) is not None:
            # 使用类的objects管理器获取最新数据
            cls = self.__class__
            refreshed = cls.objects.get(**{self.primary_key: getattr(self, self.primary_key)})
            if refreshed:
                self._data = refreshed._data.copy()
                self._dirty.clear()  # 清除脏标记
    
    def save(self) -> None:
        """保存到数据库，子类应该实现此方法"""
        raise NotImplementedError("子类必须实现save方法")
    
    def delete(self) -> None:
        """从数据库删除当前对象"""
        if hasattr(self, self.primary_key) and getattr(self, self.primary_key) is not None:
            # 使用类的objects管理器删除对象
            cls = self.__class__
            cls.objects.delete(**{self.primary_key: getattr(self, self.primary_key)})


class ModelManager:
    """模型管理器基类，提供通用的数据库操作方法"""
    
    def __init__(self, model_class):
        self.db = DatabaseManager()
        self.model_class = model_class
        self.table_name = model_class.table_name
    
    def create_table(self, force=False):
        """创建数据表"""
        raise NotImplementedError("子类必须实现create_table方法")
    
    def create(self, **kwargs):
        """创建并保存对象"""
        instance = self.model_class(**kwargs)
        instance.save()
        return instance
    
    def get(self, **kwargs):
        """根据条件获取单个对象"""
        results = self.filter(**kwargs)
        if results:
            return results[0]
        return None
    
    def get_or_create(self, defaults=None, **kwargs):
        """获取对象，如果不存在则创建"""
        defaults = defaults or {}
        instance = self.get(**kwargs)
        if instance:
            return instance, False
        
        # 合并kwargs和defaults
        params = {**kwargs, **defaults}
        return self.create(**params), True
    
    def update_or_create(self, defaults=None, **kwargs):
        """更新对象，如果不存在则创建"""
        defaults = defaults or {}
        instance = self.get(**kwargs)
        if instance:
            for key, value in defaults.items():
                setattr(instance, key, value)
            instance.save()
            return instance, False
        
        # 合并kwargs和defaults
        params = {**kwargs, **defaults}
        return self.create(**params), True
    
    def _build_where_clause(self, **kwargs):
        """构建WHERE子句"""
        where_conditions = []
        params = []
        
        for key, value in kwargs.items():
            # 处理特殊操作符，如__gt, __lt等
            if '__' in key:
                field, op = key.split('__', 1)
                if op == 'gt':
                    where_conditions.append(f"{field} > %s")
                elif op == 'lt':
                    where_conditions.append(f"{field} < %s")
                elif op == 'gte':
                    where_conditions.append(f"{field} >= %s")
                elif op == 'lte':
                    where_conditions.append(f"{field} <= %s")
                elif op == 'contains':
                    where_conditions.append(f"{field} LIKE %s")
                    value = f"%{value}%"
                elif op == 'in':
                    placeholders = ", ".join(["%%s"] * len(value))
                    where_conditions.append(f"{field} IN ({placeholders})")
                    params.extend(value)
                    continue  # 已经添加了参数，跳过下面的append
                elif op == 'isnull':
                    if value:
                        where_conditions.append(f"{field} IS NULL")
                    else:
                        where_conditions.append(f"{field} IS NOT NULL")
                    continue  # 不需要参数，跳过下面的append
            else:
                where_conditions.append(f"{key} = %s")
            
            params.append(value)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        return where_clause, params
    
    def _execute_query(self, query_type, where_clause=None, params=None, order_by=None, limit=None, offset=None, fields=None, updates=None):
        """执行查询的通用方法"""
        params = params or []
        
        if query_type == 'SELECT':
            field_list = "*" if not fields else ", ".join(fields)
            sql = f"SELECT {field_list} FROM {self.table_name}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            
            # 添加排序
            if order_by:
                sql += f" ORDER BY {order_by}"
            elif hasattr(self.model_class, 'Meta') and hasattr(self.model_class.Meta, 'ordering'):
                ordering = self.model_class.Meta.ordering
                if ordering:
                    order_clause = ", ".join(ordering)
                    sql += f" ORDER BY {order_clause}"
            
            # 添加分页
            if limit is not None:
                sql += f" LIMIT {limit}"
                if offset is not None:
                    sql += f" OFFSET {offset}"
            
            results = self.db.query(sql, tuple(params))
            return [self.model_class(**row) for row in results]
            
        elif query_type == 'COUNT':
            sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            
            result = self.db.query_one(sql, tuple(params))
            return result['count'] if result else 0
            
        elif query_type == 'EXISTS':
            sql = f"SELECT EXISTS(SELECT 1 FROM {self.table_name}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            sql += ") as exist"
            
            result = self.db.query_one(sql, tuple(params))
            return result['exist'] == 1 if result else False
            
        elif query_type == 'DELETE':
            sql = f"DELETE FROM {self.table_name}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            
            self.db.execute(sql, tuple(params))
            return True
            
        elif query_type == 'UPDATE':
            if not updates:
                return False
                
            set_conditions = []
            update_params = []
            
            for key, value in updates.items():
                set_conditions.append(f"{key} = %s")
                update_params.append(value)
            
            set_clause = ", ".join(set_conditions)
            
            sql = f"UPDATE {self.table_name} SET {set_clause}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            
            all_params = update_params + params
            self.db.execute(sql, tuple(all_params))
            return True
            
        return None
    
    def filter(self, **kwargs):
        """根据条件过滤对象"""
        where_clause, params = self._build_where_clause(**kwargs)
        return self._execute_query('SELECT', where_clause, params)
    
    def all(self, limit=None, offset=None, order_by=None):
        """获取所有对象"""
        return self._execute_query('SELECT', limit=limit, offset=offset, order_by=order_by)
    
    def exists(self, **kwargs):
        """检查是否存在符合条件的记录"""
        where_clause, params = self._build_where_clause(**kwargs)
        return self._execute_query('EXISTS', where_clause, params)
    
    def count(self, **kwargs):
        """统计符合条件的记录数量"""
        where_clause, params = self._build_where_clause(**kwargs)
        return self._execute_query('COUNT', where_clause, params)
    
    def delete(self, **kwargs):
        """根据条件删除对象"""
        where_clause, params = self._build_where_clause(**kwargs)
        return self._execute_query('DELETE', where_clause, params)
    
    def update(self, updates, **kwargs):
        """根据条件更新对象"""
        where_clause, params = self._build_where_clause(**kwargs)
        return self._execute_query('UPDATE', where_clause, params, updates=updates)
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


class CCTVNewsManager(ModelManager):
    """CCTV新闻模型管理器，类似Django的objects"""
    
    def __init__(self):
        # 注意：这里需要在CCTVNews类定义后再初始化
        # 由于Python的类定义顺序，这个初始化会在CCTVNews定义后执行
        self.db = DatabaseManager()
        self.model_class = None  # 将在CCTVNews类中设置
        self.table_name = 'cctv_news'
    
    def create_table(self, force=False):
        """创建数据表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `cctv_news` (
            `id` int NOT NULL AUTO_INCREMENT COMMENT 'Primary Key',
            `create_time` datetime DEFAULT NULL COMMENT 'Create Time',
            `title` varchar(255) DEFAULT NULL COMMENT 'Title',
            `content` longtext COMMENT 'Content',
            `ai_content` longtext COMMENT 'AI Content',
            `publish_date` datetime DEFAULT NULL COMMENT 'Publish Date',
            PRIMARY KEY (`id`),
            INDEX `idx_publish_date` (`publish_date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='CCTV News'
        """
        self.db.execute(create_table_sql)
    
    def save_combined_news(self, all_news_content, publish_date):
        """保存合并后的新闻内容"""
        if self.exists(publish_date=publish_date):
            return False
        
        title = f"新闻联播内容汇总 - {publish_date}"
        combined_content = "\n\n".join(all_news_content)
        
        self.create(
            title=title,
            content=combined_content,
            publish_date=publish_date
        )
        return True
    
    def get_latest_news(self, limit=10):
        """获取最新的新闻"""
        return self.all(limit=limit, order_by="publish_date DESC")
    
    def search_by_keyword(self, keyword, limit=20):
        """根据关键词搜索新闻"""
        # 使用filter方法实现关键词搜索
        # 由于需要OR条件，我们需要分别查询标题和内容，然后合并结果
        title_results = self.filter(title__contains=keyword)
        content_results = self.filter(content__contains=keyword)
        
        # 合并结果并去重
        all_results = {}
        for news in title_results + content_results:
            if news.id not in all_results:
                all_results[news.id] = news
        
        # 按发布日期排序并限制数量
        sorted_results = sorted(
            all_results.values(), 
            key=lambda x: x.publish_date if hasattr(x, 'publish_date') else datetime.min, 
            reverse=True
        )
        
        return sorted_results[:limit]


class CCTVNews(ModelBase):
    """CCTV新闻模型类，类似Django的Model"""
    
    # 表名定义
    table_name = 'cctv_news'
    
    # 字段定义
    fields = ['id', 'create_time', 'title', 'content', 'ai_content', 'publish_date']
    
    # 创建管理器实例
    objects = CCTVNewsManager()
    
    # 元数据类，类似Django的Meta
    class Meta:
        ordering = ['-publish_date']  # 默认排序
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 设置默认值
        if not hasattr(self, 'id'):
            self.id = None
        if not hasattr(self, 'create_time'):
            self.create_time = datetime.now()
        if not hasattr(self, 'ai_content'):
            self.ai_content = None
    
    def __str__(self):
        return f"CCTVNews(id={self.id}, title='{self.title}', publish_date='{self.publish_date}')"
    
    def __repr__(self):
        return self.__str__()
    
    def save(self):
        """保存当前对象到数据库"""
        if self.id is None:
            # 新建记录
            data = {
                'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(self.create_time, datetime) else self.create_time,
                'title': self.title,
                'content': self.content,
                'ai_content': self.ai_content,
                'publish_date': self.publish_date.strftime('%Y-%m-%d') if isinstance(self.publish_date, datetime) else self.publish_date
            }
            # 使用管理器的create方法创建记录
            created = CCTVNews.objects.create(**data)
            self.id = created.id
            self._dirty.clear()  # 清除脏标记
        else:
            # 如果有修改才更新
            if self.is_dirty():
                # 只更新修改过的字段
                dirty_fields = self.get_dirty_fields()
                if dirty_fields:
                    updates = {}
                    
                    for key, value in dirty_fields.items():
                        if key != 'id':  # 不更新id字段
                            # 处理日期时间类型
                            if key == 'create_time' and isinstance(value, datetime):
                                value = value.strftime('%Y-%m-%d %H:%M:%S')
                            elif key == 'publish_date' and isinstance(value, datetime):
                                value = value.strftime('%Y-%m-%d')
                            updates[key] = value
                    
                    if updates:  # 确保有字段需要更新
                        # 使用管理器的update方法更新记录
                        CCTVNews.objects.update(updates, id=self.id)
                
                self._dirty.clear()  # 清除脏标记
    
    def delete(self):
        """从数据库删除当前对象"""
        if self.id is not None:
            CCTVNews.objects.delete(id=self.id)
    
    def refresh_from_db(self):
        """从数据库刷新对象数据"""
        if self.id is not None:
            refreshed = CCTVNews.objects.get(id=self.id)
            if refreshed:
                self._data = refreshed._data
                self._dirty.clear()  # 清除脏标记
    
    @property
    def summary(self):
        """获取内容摘要"""
        if self.content:
            max_length = 200
            if len(self.content) > max_length:
                return self.content[:max_length] + '...'
            return self.content
        return ""
    
    @classmethod
    def create_table(cls, force=False):
        """创建数据表"""
        cls.objects.create_table(force)
    
    @classmethod
    def close_connection(cls):
        """关闭数据库连接"""
        cls.objects.close()


# 设置CCTVNewsManager的model_class属性
CCTVNews.objects.model_class = CCTVNews

# 快捷访问方式
CCTVNewsModel = CCTVNews  # 向下兼容