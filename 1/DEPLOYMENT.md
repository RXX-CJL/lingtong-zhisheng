# 智瞳智慧交管系统 - 部署文档

## 目录
1. [系统架构](#系统架构)
2. [后端部署](#后端部署)
3. [前端管理后台部署](#前端管理后台部署)
4. [微信小程序发布](#微信小程序发布)
5. [K230设备部署](#k230设备部署)
6. [环境变量配置](#环境变量配置)
7. [健康检查](#健康检查)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  微信小程序   │  │  Web管理后台  │  │   K230边缘设备       │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
└─────────┼──────────────────┼─────────────────────┼───────────────┘
          │                  │                     │
          ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API网关层                                 │
│                  FastAPI (0.0.0.0:8001)                         │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        服务层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  违规检测API  │  │  图像识别模块  │  │    JWT认证服务       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层                                     │
│              SQLite (zhitong_violations.db)                     │
│              + uploads/ (图片存储)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 后端部署

### 环境要求
- Python 3.9+
- pip 20.0+
- 操作系统：Linux / Windows / macOS

### 安装步骤

1. **进入项目目录**
```bash
cd e:\output\1\api
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# Linux/macOS
export DASHSCOPE_API_KEY=your_api_key_here

# Windows PowerShell
$env:DASHSCOPE_API_KEY="your_api_key_here"
```

4. **启动服务**
```bash
# 开发模式（自动重载）
python app.py

# 生产模式
uvicorn app:app --host 0.0.0.0 --port 8001
```

5. **开机自启（Linux）**
```bash
# 创建 systemd 服务文件
sudo nano /etc/systemd/system/zhitong-api.service

# 添加内容：
[Unit]
Description=智瞳智慧交管系统API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/api
Environment="DASHSCOPE_API_KEY=your_key"
ExecStart=/usr/local/bin/uvicorn app:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable zhitong-api
sudo systemctl start zhitong-api
```

---

## 前端管理后台部署

### 环境要求
- Node.js 16+
- npm 8+

### 构建步骤

1. **进入项目目录**
```bash
cd e:\output\1\web-admin
```

2. **安装依赖**
```bash
npm install
```

3. **开发模式运行**
```bash
npm run dev
```

4. **生产构建**
```bash
npm run build
```

5. **部署到静态服务器**
```bash
# 构建产物位于 dist/ 目录
# 使用 nginx 部署示例：
# sudo cp -r dist/* /var/www/html/
```

### Nginx 配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8001/uploads/;
    }
}
```

---

## 微信小程序发布

### 开发环境配置

1. **打开微信开发者工具**
2. **导入项目**
   - 目录：`e:\output\1\wechat-miniprogram`
   - AppID：使用测试号或正式号

3. **配置API地址**
   - 文件：`app.js`
   - 确保 `baseUrl` 指向后端服务地址

### 审核发布流程

1. **代码审查**
```bash
# 在微信开发者工具中
# 点击"工具" → "代码质量检测"
```

2. **上传代码**
```bash
# 在微信开发者工具中
# 点击"上传"按钮
# 版本号：x.y.z
# 备注：本次更新内容
```

3. **提交审核**
```bash
# 登录微信公众平台
# https://mp.weixin.qq.com/
# 进入"开发管理" → "开发版本"
# 找到刚上传的版本，点击"提交审核"
```

4. **发布上线**
```bash
# 审核通过后
# 在"版本管理"中点击"发布"
```

---

## K230设备部署

### SD卡内容准备

```
sdcard/
├── config/
│   └── config.json          # 设备配置文件
├── models/
│   └── best.pt              # YOLO模型文件
├── app/
│   └── main.py              # K230应用程序
└── startup.sh               # 启动脚本
```

### 配置文件示例

```json
{
  "device_id": "K230-001",
  "server_url": "http://your-server-ip:8001",
  "upload_interval": 5,
  "detection_threshold": 0.5,
  "camera_params": {
    "width": 640,
    "height": 480,
    "fps": 30
  }
}
```

### 烧录步骤

1. **格式化SD卡**
```bash
# 使用 FAT32 格式
mkfs.vfat /dev/sdX1
```

2. **复制文件**
```bash
cp -r k230_app/* /mnt/sdcard/
```

3. **插入K230设备**
```bash
# 将SD卡插入K230开发板
# 上电启动
```

4. **验证运行**
```bash
# 查看设备日志
ssh root@k230-ip
tail -f /var/log/zhitong.log
```

---

## 环境变量配置

### 后端环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DASHSCOPE_API_KEY | 阿里云DashScope API密钥 | - |
| DATABASE_URL | 数据库连接URL | sqlite:///./zhitong_violations.db |
| LOG_LEVEL | 日志级别 | INFO |
| UPLOAD_DIR | 上传文件目录 | uploads/ |

### 前端环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| VITE_API_BASE_URL | 后端API地址 | /api |

### 小程序环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| baseUrl | 后端API地址 | http://127.0.0.1:8001 |

---

## 健康检查

### API健康检查
```bash
curl http://localhost:8001/health
```

响应示例：
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "yolo_available": true,
  "dashscope_available": true,
  "uploads_dir_exists": true,
  "db_exists": true,
  "overall": "ok"
}
```

### 前端可用性检查
```bash
curl -I http://localhost:5173/
```

### API文档
```bash
# 访问自动生成的API文档
# http://localhost:8001/docs
# http://localhost:8001/redoc
```

---

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |

---

## 常见问题

### Q1: 后端启动失败
```bash
# 检查端口是否被占用
netstat -tlnp | grep 8001

# 检查依赖是否安装完整
pip list | grep -E "(fastapi|uvicorn|sqlalchemy)"
```

### Q2: 前端无法访问后端API
```bash
# 检查Vite代理配置
# web-admin/vite.config.js

# 检查后端服务是否正常运行
curl http://localhost:8001/
```

### Q3: 图像识别模块加载失败
```bash
# 检查DashScope API密钥
echo $DASHSCOPE_API_KEY

# 检查网络连接
curl -I https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
```

### Q4: 数据库表缺失
```bash
# 重新初始化数据库
python -c "from database import init_db; init_db()"
```

---

## 技术支持

如需帮助，请联系开发团队或查看项目文档。

---

**版本**: 2.0.0  
**日期**: 2026-06-12