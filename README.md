# 股票数据服务 Django 框架

这是一个灵活的股票数据服务 Django 框架，用户只需要在指定目录添加数据获取逻辑、接口函数和路由即可快速构建股票数据API服务。

## 项目结构

```
stock_data_service/
├── manage.py             # Django管理脚本
├── start.sh              # Linux/Mac启动脚本
├── start.bat             # Windows启动脚本
├── config.py             # 配置文件
├── requirements.txt      # 依赖文件
├── .env.example          # 环境变量模板
├── stock_data_service/   # 项目主目录
│   ├── __init__.py
│   ├── settings.py       # 项目设置
│   ├── urls.py           # 主URL配置
│   ├── asgi.py           # ASGI配置
│   └── wsgi.py           # WSGI配置
├── stock_data/           # 股票数据应用
│   ├── __init__.py
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── urls.py           # URL配置
│   └── services.py       # 服务层
├── stock_strategy/       # 股票策略应用
│   ├── __init__.py
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── urls.py           # URL配置
│   └── services.py       # 服务层
├── cctv_news/            # 新闻数据应用
│   ├── __init__.py
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── urls.py           # URL配置
│   └── services.py       # 服务层
├── common/               # 公共组件
│   ├── __init__.py
│   ├── response.py       # 响应工具
│   └── validators.py     # 验证工具
├── docs/                 # 文档目录
└── data/                 # 数据存储目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置项
```

### 3. 启动服务

#### 使用启动脚本（推荐）

在Linux/Mac系统上：
```bash
# 添加执行权限
chmod +x start.sh
# 运行启动脚本
./start.sh
```

在Windows系统上：
```bash
# 运行启动脚本
start.bat
```

#### 手动启动

```bash
# 执行数据库迁移
python manage.py migrate

# 开发模式启动
python manage.py runserver

# 指定IP和端口启动（允许外部访问）
python manage.py runserver 0.0.0.0:8000
```

### 4. 测试服务

访问以下地址测试服务是否正常运行：
- http://localhost:8000/ - 服务主页（API端点列表）
- http://localhost:8000/api/stock/realtime - 实时股票数据
- http://localhost:8000/api/news/cctv - CCTV新闻数据
- http://localhost:8000/api/strategy/index_rps - 指数RPS强度排名

## 使用指南

### 添加新的Django应用

```bash
python manage.py startapp my_app
```

### 添加新的数据模型

在新应用的`models.py`文件中定义数据模型：

```python
# my_app/models.py
from django.db import models

class MyData(models.Model):
    name = models.CharField(max_length=100)
    value = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
```

### 添加新的服务层

在新应用中创建`services.py`文件：

```python
# my_app/services.py
from typing import Dict, List
from .models import MyData

class MyDataService:
    @staticmethod
    def get_data(name: str) -> Dict:
        # 实现你的数据获取逻辑
        data = MyData.objects.filter(name=name).first()
        if data:
            return {"name": data.name, "value": data.value}
        return {"error": "Data not found"}
```

### 添加新的视图函数

在新应用的`views.py`文件中定义视图函数：

```python
# my_app/views.py
from django.http import JsonResponse
from common.response import success_response, error_response
from .services import MyDataService

def get_my_data(request, name):
    try:
        data = MyDataService.get_data(name)
        return success_response(data)
    except Exception as e:
        return error_response(str(e))
```

### 添加新的URL配置

在新应用中创建`urls.py`文件：

```python
# my_app/urls.py
from django.urls import path
from . import views

app_name = 'my_app'

urlpatterns = [
    path('data/<str:name>/', views.get_my_data, name='get_my_data'),
]
```

### 注册应用URL

在项目主URL配置文件中注册新应用的URL：

```python
# stock_data_service/urls.py
from django.urls import path, include

urlpatterns = [
    # 其他URL配置
    path('api/my/', include('my_app.urls')),
]
```

### 使用工具函数

#### 响应工具

```python
from common.response import success_response, error_response

# 成功响应
return success_response(data, '操作成功')

# 错误响应
return error_response('错误信息', 400)
```

## 启动脚本说明

### Linux/Mac启动脚本 (start.sh)

启动脚本会自动执行以下操作：
1. 设置环境变量
2. 检查并激活虚拟环境（如果存在）
3. 安装依赖
4. 执行数据库迁移
5. 启动Django服务器（绑定到0.0.0.0:8000）

### Windows启动脚本 (start.bat)

Windows启动脚本执行相同的操作，但适用于Windows环境：
1. 设置环境变量
2. 检查并激活虚拟环境（如果存在）
3. 安装依赖
4. 执行数据库迁移
5. 启动Django服务器（绑定到0.0.0.0:8000）

## 开发最佳实践

### 1. 数据获取逻辑

- 将所有数据获取逻辑放在服务层（services.py）
- 使用类封装数据获取功能
- 提供错误处理和日志记录
- 使用缓存提高性能

### 2. API设计

- 每个功能模块创建独立的应用
- 使用Django REST framework（可选）
- 提供清晰的API文档
- 统一响应格式

### 3. 错误处理

- 使用try/except捕获异常
- 返回统一格式的错误响应
- 记录错误日志
- 提供有用的错误信息