# 股票数据服务 (Stock Data Service)

一个基于Django的股票数据采集、分析和量化策略回测平台，提供完整的股票数据API服务和量化交易策略回测功能。

## 📋 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [项目架构](#项目架构)
- [功能模块](#功能模块)
- [环境要求](#环境要求)
- [安装部署](#安装部署)
- [API文档](#api文档)
- [定时任务](#定时任务)
- [开发指南](#开发指南)
- [许可证](#许可证)

## 🚀 项目概述

股票数据服务是一个综合性的金融数据平台，主要功能包括：

- **股票数据采集**：实时获取个股、行业板块、市场数据
- **新闻资讯分析**：CCTV新闻联播内容采集与AI分析
- **量化策略回测**：支持多种技术指标策略的历史回测
- **用户管理系统**：完整的用户注册、登录、权限管理
- **论坛社区**：用户交流讨论平台
- **定时任务调度**：自动化数据更新和维护

## 🛠 技术栈

### 后端框架
- **Django 4.2.7** - Web框架
- **Django REST Framework 3.14.0** - API框架
- **Python 3.13** - 编程语言

### 数据库
- **MySQL** - 主数据库
- **PyMySQL** - MySQL数据库连接器

### 数据获取
- **AkShare** - 股票数据获取
- **PyWenCai** - 同花顺数据接口
- **Requests** - HTTP请求库
- **Playwright** - 网页自动化

### 量化分析
- **Backtrader** - 量化策略回测框架
- **Pandas** - 数据分析
- **NumPy** - 数值计算

### 任务调度
- **Django-Crontab** - 定时任务管理

### 其他工具
- **Django-CORS-Headers** - 跨域请求处理
- **Loguru** - 日志管理
- **Python-Dotenv** - 环境变量管理

## 🏗 项目架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端应用                              │
│                    (Vue.js/React)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/HTTPS API
┌─────────────────────┴───────────────────────────────────────┐
│                   Django REST API                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ 股票数据API │ │ 用户管理API │ │ 量化策略API │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ 新闻资讯API │ │ 论坛社区API │ │ 定时任务API │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                    业务逻辑层                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │数据采集服务 │ │策略回测引擎 │ │新闻分析服务 │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                    数据访问层                                │
│                   Django ORM                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                    MySQL 数据库                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  股票数据   │ │  用户数据   │ │  策略数据   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 数据流架构

```
外部数据源 → 数据采集 → 数据处理 → 数据存储 → API服务 → 前端展示
    ↓           ↓         ↓         ↓        ↓        ↓
AkShare     定时任务   数据清洗   MySQL    REST API  用户界面
同花顺      爬虫程序   格式转换   缓存层   认证授权   图表展示
新闻网站    实时更新   异常处理   索引优化  限流控制   交互操作
```

## 📦 功能模块

### 1. 股票数据模块 (`stock_data`)
- **行业板块数据**：板块基本信息、实时行情、日频数据
- **个股基本信息**：股票代码、名称、行业分类
- **实时行情数据**：价格、涨跌幅、成交量等
- **市场摘要数据**：整体市场统计信息

### 2. 个股数据模块 (`indival_stock_data`)
- **个股详细信息**：完整的股票基本面数据
- **日频历史数据**：OHLCV数据
- **实时行情更新**：分钟级数据更新
- **财务报表数据**：资产负债表、利润表、现金流量表
- **业绩报告数据**：季度和年度业绩指标

### 3. 量化策略模块 (`quantitative_strategy`)
- **策略配置管理**：策略参数配置和管理
- **回测任务调度**：异步回测任务处理
- **回测结果分析**：收益率、夏普比率、最大回撤等指标
- **策略性能统计**：历史表现统计分析

#### 支持的策略类型：
- **移动平均策略**：MA交叉策略
- **MACD策略**：MACD指标策略
- **RSI策略**：相对强弱指标策略
- **布林带策略**：布林带突破策略
- **KDJ策略**：随机指标策略
- **BIAS策略**：乖离率策略
- **PSY策略**：心理线指标策略
- **WR策略**：威廉指标策略

### 4. 新闻资讯模块 (`cctv_news`)
- **新闻采集**：CCTV新闻联播内容自动采集
- **AI内容分析**：新闻内容智能分析和摘要
- **新闻检索**：按日期、关键词检索新闻

### 5. 用户管理模块 (`user_management`)
- **用户注册登录**：完整的用户认证系统
- **权限管理**：基于角色的访问控制
- **邀请码系统**：用户邀请注册机制
- **Token认证**：API访问令牌管理

### 6. 论坛社区模块 (`forum`)
- **帖子管理**：用户发帖、编辑、删除
- **评论系统**：帖子评论和回复
- **用户互动**：点赞、收藏等社交功能

### 7. 定时任务模块 (`scheduled_tasks`)
- **数据更新任务**：股票数据定时更新
- **新闻采集任务**：新闻内容定时抓取
- **系统维护任务**：日志清理、状态检查
- **任务监控**：任务执行状态监控

### 8. 股票策略模块 (`stock_strategy`)
- **行业轮动策略**：基于行业板块的投资策略
- **策略信号生成**：买卖信号生成和推送

### 9. 股票市场模块 (`stock_market`)
- **市场数据统计**：整体市场数据分析
- **市场指标计算**：技术指标计算服务

### 10. MCP服务模块 (`mcp_service`)
- **Tushare数据接口**：基于 FastMCP 的工具集成，支持各类数据接口
- **SSE传输支持**：支持大模型或 AI 助手通过 SSE 协议直连访问数据
- **模块化工具库**：提供可扩展的工具和资源，便于直接挂载和调试

## 💻 环境要求

- **Python**: 3.13+
- **MySQL**: 5.7+ 或 8.0+
- **操作系统**: Linux/macOS/Windows
- **内存**: 建议4GB+
- **磁盘空间**: 建议20GB+

## 🚀 安装部署

### 1. 环境准备

#### 1.1 安装Python 3.13
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv python3.13-dev

# CentOS/RHEL
sudo yum install python3.13 python3.13-venv python3.13-devel

# macOS (使用Homebrew)
brew install python@3.13
```

#### 1.2 安装MySQL
```bash
# Ubuntu/Debian
sudo apt install mysql-server mysql-client

# CentOS/RHEL
sudo yum install mysql-server mysql

# macOS
brew install mysql
```

#### 1.3 创建数据库
```sql
-- 登录MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE stock_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（可选）
CREATE USER 'stock_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stock_db.* TO 'stock_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. 项目部署

#### 2.1 克隆项目
```bash
git clone <repository-url>
cd stock_data_service
```

#### 2.2 创建虚拟环境
```bash
python3.13 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

#### 2.3 安装依赖
```bash
pip install -r requirements.txt
```

#### 2.4 配置数据库
编辑 `stock_data_service/settings.py` 文件中的数据库配置：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stock_db',                    # 数据库名
        'USER': 'your_username',               # 数据库用户名
        'PASSWORD': 'your_password',           # 数据库密码
        'HOST': 'localhost',                   # 数据库主机
        'PORT': '3306',                        # 数据库端口
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

**注意**: 本项目不使用 `.env.example` 文件，所有配置直接在 `settings.py` 中修改。

#### 2.5 数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. 启动服务

#### 3.1 开发环境启动
```bash
python manage.py runserver 0.0.0.0:8000
```

#### 3.2 生产环境启动
```bash
# 使用提供的启动脚本
chmod +x start.sh
./start.sh

# 或者直接运行
python manage.py runserver 0.0.0.0:8001
```

### 4. 配置定时任务

#### 4.1 添加定时任务到系统crontab
```bash
# 添加定时任务
python manage.py crontab add

# 查看已添加的定时任务
python manage.py crontab show

# 移除定时任务
python manage.py crontab remove
```

#### 4.2 定时任务说明
项目中配置的定时任务包括：

- **新闻采集**：每天20:25和21:25执行新闻联播采集
- **新闻分析**：每天20:35和21:35执行新闻内容AI分析
- **行业板块数据**：每天16-19点每小时更新行业板块数据
- **个股数据更新**：每天16:40和23:40更新个股日频数据
- **系统维护**：每天凌晨2点清理旧日志，每30分钟检查任务状态

### 5. 验证部署

#### 5.1 健康检查
```bash
curl http://localhost:8001/health
```

#### 5.2 API测试
```bash
# 获取API端点信息
curl http://localhost:8001/

# 测试股票数据API
curl http://localhost:8001/api/stock/industry-sectors/
```

### 6. MCP服务部署

本项目提供基于 FastMCP 的 MCP（Model Context Protocol）服务器，支持 SSE 传输方式。

#### 6.1 安装依赖
确保已安装 `mcp[cli]` 依赖：
```bash
pip install -r requirements.txt
```

#### 6.2 启动服务 (SSE方式)

**方式一：直接运行（默认）**
```bash
python mcp_service/server.py --host 0.0.0.0 --port 8008
```
默认监听 `0.0.0.0:8008`，可在 MCP 客户端中以 SSE 方式连接。SSE 的挂载路径前缀默认为 `/tushare/mcp/sse`。

**方式二：使用 MCP CLI（推荐开发调试）**
```bash
# 交互开发/调试
mcp dev mcp_service/server.py

# 或运行
mcp run mcp_service/server.py
```
> 注：详细的 MCP 工具及资源说明，请参考 `docs/mcp_service.md`。

## 📚 API文档

### API基础信息
- **Base URL**: `http://your-domain:8001`
- **认证方式**: Token认证
- **响应格式**: JSON
- **字符编码**: UTF-8

### 统一响应格式

#### 成功响应
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        // 具体数据
    }
}
```

#### 错误响应
```json
{
    "code": 400,
    "message": "error message",
    "timestamp": "2024-01-01T12:00:00"
}
```

### 主要API端点

#### 1. 股票数据API (`/api/stock/`)
- `GET /api/stock/industry-sectors/` - 获取行业板块列表
- `GET /api/stock/industry-sectors/{id}/` - 获取板块详情
- `GET /api/stock/industry-sectors/{id}/daily-data/` - 获取板块日频数据
- `GET /api/stock/stocks/` - 获取股票列表
- `GET /api/stock/stocks/{code}/realtime/` - 获取股票实时行情

#### 2. 个股数据API (`/api/individual-stock/`)
- `GET /api/individual-stock/stocks/` - 获取个股列表
- `GET /api/individual-stock/stocks/{code}/` - 获取个股详情
- `GET /api/individual-stock/stocks/{code}/daily-data/` - 获取个股日频数据
- `GET /api/individual-stock/stocks/{code}/performance/` - 获取个股业绩数据

#### 3. 量化策略API (`/api/quant/`)
- `GET /api/quant/strategies/` - 获取策略列表
- `POST /api/quant/backtest/` - 创建回测任务
- `GET /api/quant/backtest/{task_id}/` - 获取回测结果
- `GET /api/quant/backtest/{task_id}/chart/` - 获取回测图表

#### 4. 新闻资讯API (`/api/news/`)
- `GET /api/news/` - 获取新闻列表
- `GET /api/news/{id}/` - 获取新闻详情
- `GET /api/news/search/` - 搜索新闻

#### 5. 用户管理API (`/api/user/`)
- `POST /api/user/register/` - 用户注册
- `POST /api/user/login/` - 用户登录
- `POST /api/user/logout/` - 用户登出
- `GET /api/user/profile/` - 获取用户信息

#### 6. 论坛API (`/api/forum/`)
- `GET /api/forum/posts/` - 获取帖子列表
- `POST /api/forum/posts/` - 创建帖子
- `GET /api/forum/posts/{id}/` - 获取帖子详情
- `POST /api/forum/posts/{id}/comments/` - 添加评论

详细的API文档请参考 `docs/` 目录下的相关文档。

## ⏰ 定时任务

项目使用 `django-crontab` 管理定时任务，主要任务包括：

### 数据采集任务
- **新闻采集**：`25 20,21 * * *` - 每天20:25和21:25采集CCTV新闻
- **新闻分析**：`35 20,21 * * *` - 每天20:35和21:35分析新闻内容
- **行业板块更新**：`1 16,17,18,19 * * *` - 每天16-19点更新行业数据
- **个股数据更新**：`40 16,23 * * *` - 每天16:40和23:40更新个股数据

### 系统维护任务
- **日志清理**：`0 2 * * *` - 每天凌晨2点清理旧日志
- **任务状态检查**：`*/30 * * * *` - 每30分钟检查任务状态

### 任务管理命令
```bash
# 查看所有定时任务
python manage.py crontab show

# 添加定时任务到系统
python manage.py crontab add

# 移除所有定时任务
python manage.py crontab remove

# 手动执行特定任务
python manage.py shell -c "from scheduled_tasks.tasks import fetch_cctv_news; fetch_cctv_news()"
```

## 🔧 开发指南

### 项目结构说明
```
stock_data_service/
├── stock_data_service/          # Django项目配置
│   ├── settings.py             # 项目设置
│   ├── urls.py                 # 主URL配置
│   └── wsgi.py                 # WSGI配置
├── common/                     # 公共模块
│   ├── response.py             # 统一响应格式
│   ├── validators.py           # 数据验证器
│   └── sensitive_words.py      # 敏感词过滤
├── stock_data/                 # 股票数据模块
├── indival_stock_data/         # 个股数据模块
├── quantitative_strategy/      # 量化策略模块
├── cctv_news/                  # 新闻资讯模块
├── user_management/            # 用户管理模块
├── forum/                      # 论坛社区模块
├── scheduled_tasks/            # 定时任务模块
├── stock_strategy/             # 股票策略模块
├── stock_market/               # 股票市场模块
├── docs/                       # 文档目录
├── logs/                       # 日志目录
├── requirements.txt            # 依赖包列表
├── manage.py                   # Django管理脚本
├── deploy.sh                   # 部署脚本
└── start.sh                    # 启动脚本
```

### 开发规范

#### 1. 代码规范
- 遵循PEP 8代码风格
- 使用有意义的变量和函数名
- 添加必要的注释和文档字符串
- 所有组件都需要添加注释，包含功能、参数、返回值、事件等信息

#### 2. API设计规范
- 统一使用 `success_response` 和 `error_response` 返回数据
- RESTful API设计原则
- 合理的HTTP状态码使用
- 统一的错误处理机制

#### 3. 数据库设计规范
- 合理的表结构设计
- 适当的索引优化
- 数据完整性约束
- 软删除机制

#### 4. 页面设计原则
- Vue页面遵循单一职责原则
- 每个页面只负责一个功能
- 避免页面过于复杂

### 本地开发环境搭建

#### 1. 开发工具推荐
- **IDE**: PyCharm Professional / VS Code
- **数据库工具**: MySQL Workbench / Navicat
- **API测试**: Postman / Insomnia
- **版本控制**: Git

#### 2. 开发环境配置
```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行开发服务器
python manage.py runserver 0.0.0.0:8000
```

#### 3. 测试
```bash
# 运行单元测试
python manage.py test

# 运行特定应用的测试
python manage.py test stock_data

# 使用pytest运行测试
pytest
```

### 部署注意事项

#### 1. 生产环境配置
- 设置 `DEBUG = False`
- 配置正确的 `ALLOWED_HOSTS`
- 使用环境变量管理敏感信息
- 配置HTTPS和安全头

#### 2. 性能优化
- 数据库查询优化
- 适当使用缓存
- 静态文件CDN
- 数据库连接池

#### 3. 监控和日志
- 配置日志轮转
- 监控系统资源使用
- API性能监控
- 错误报警机制

## 📄 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](LICENSE) 文件。

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目。

### 贡献流程
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 项目Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com

---

**注意**: 本项目仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。