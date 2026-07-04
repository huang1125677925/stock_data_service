# Linux服务器部署指南

本文档提供在Linux服务器上部署股票数据服务的详细步骤，包括定时任务的配置。

## 1. 环境准备

### 系统要求
- Linux服务器（推荐Ubuntu 20.04或CentOS 8）
- Python 3.8+
- MySQL 5.7+
- Git

### 安装依赖
```bash
# Ubuntu
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git mysql-server

# CentOS
sudo dnf install -y python3 python3-pip git mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

## 2. 获取代码

```bash
# 克隆代码库
git clone <仓库地址> stock_data_service
cd stock_data_service

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 3. 配置数据库

```bash
# 登录MySQL
mysql -u root -p

# 在MySQL中执行
CREATE DATABASE stock_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'stock_user'@'localhost' IDENTIFIED BY '安全密码';
GRANT ALL PRIVILEGES ON stock_db.* TO 'stock_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 4. 配置环境变量

创建`.env`文件：

```bash
cp .env.example .env
```

编辑`.env`文件，设置数据库连接信息和其他配置：

```
DB_NAME=stock_db
DB_USER=stock_user
DB_PASSWORD=安全密码
DB_HOST=localhost
DB_PORT=3306
SECRET_KEY=生成一个安全的密钥
DEBUG=False
```

## 5. 初始化应用

```bash
# 创建日志目录
mkdir -p logs

# 执行数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

## 6. 配置定时任务

### 使用django-crontab（推荐）

```bash
# 添加定时任务到crontab
python manage.py crontab add

# 查看已添加的定时任务
python manage.py crontab show
```

### 手动配置crontab

如果需要手动配置，可以编辑crontab：

```bash
crontab -e
```

添加以下内容（请根据实际路径调整）：

```
# 股票数据服务定时任务
PYTHONPATH=/path/to/stock_data_service
DJANGO_SETTINGS_MODULE=stock_data_service.settings

# 每天凌晨2点清理旧日志
0 2 * * * cd /path/to/stock_data_service && venv/bin/python manage.py runtask cleanup_old_logs

# 每30分钟检查任务状态
*/30 * * * * cd /path/to/stock_data_service && venv/bin/python manage.py runtask check_task_status

```

## 7. 启动服务

### 使用启动脚本

```bash
# 添加执行权限
chmod +x start.sh

# 启动服务
./start.sh
```

### 使用Gunicorn和Supervisor（生产环境推荐）

安装Gunicorn和Supervisor：

```bash
pip install gunicorn
sudo apt install -y supervisor  # Ubuntu
# 或
sudo dnf install -y supervisor  # CentOS
```

创建Supervisor配置文件`/etc/supervisor/conf.d/stock_data_service.conf`：

```ini
[program:stock_data_service]
command=/path/to/stock_data_service/venv/bin/gunicorn stock_data_service.wsgi:application --workers 3 --bind 0.0.0.0:8000
directory=/path/to/stock_data_service
user=<your_user>
autostart=true
autorestart=true
stdout_logfile=/path/to/stock_data_service/logs/gunicorn_stdout.log
stderr_logfile=/path/to/stock_data_service/logs/gunicorn_stderr.log
environment=PYTHONPATH="/path/to/stock_data_service",DJANGO_SETTINGS_MODULE="stock_data_service.settings"
```

重新加载Supervisor配置并启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start stock_data_service
```

## 8. 配置Nginx（可选）

安装Nginx：

```bash
sudo apt install -y nginx  # Ubuntu
# 或
sudo dnf install -y nginx  # CentOS
```

创建Nginx配置文件`/etc/nginx/sites-available/stock_data_service`：

```nginx
server {
    listen 80;
    server_name your_domain.com;  # 替换为你的域名或IP

    location /static/ {
        alias /path/to/stock_data_service/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用站点并重启Nginx：

```bash
# Ubuntu
sudo ln -s /etc/nginx/sites-available/stock_data_service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# CentOS
sudo cp /etc/nginx/sites-available/stock_data_service /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl restart nginx
```

## 9. 故障排查

### 检查日志

```bash
# 查看应用日志
cat logs/django.log

# 查看Gunicorn日志
cat logs/gunicorn_stdout.log
cat logs/gunicorn_stderr.log
```

### 检查定时任务

```bash
# 查看crontab配置
crontab -l

# 查看django-crontab配置
python manage.py crontab show
```

## 10. 安全建议

1. 使用防火墙限制端口访问
2. 配置SSL证书实现HTTPS
3. 定期更新系统和依赖包
4. 使用非root用户运行服务
5. 设置强密码并定期更换
6. 配置数据库备份策略
