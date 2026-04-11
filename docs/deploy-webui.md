# Web 服务部署与启动手册

本文档覆盖后端 API 服务 + 前端 Web 页面的启动方式，适用于本地开发、云服务器和 Docker 三种场景。

---

## 前置条件

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | >= 3.10 | 后端运行环境 |
| Node.js | >= 18 | 前端构建（若 `WEBUI_AUTO_BUILD=true` 则自动执行） |
| pip 依赖 | — | `pip install -r requirements.txt` |

在 `.env` 中至少配置一个 AI API Key（如 `GEMINI_API_KEY`、`ANTHROPIC_API_KEY`、`DEEPSEEK_API_KEY`），否则分析功能无法使用。

```bash
# 首次使用：从模板创建配置文件
cp .env.example .env
# 编辑 .env，填入必要配置
```

---

## 方式一：一键启动（推荐本地使用）

```bash
# 仅启动 Web 服务，不执行分析
python main.py --serve-only

# 启动 Web 服务，同时立即执行一次分析
python main.py --serve
```

启动后访问 **http://localhost:8000**

> 首次启动时 `WEBUI_AUTO_BUILD=true`（默认）会自动执行 `npm install && npm run build`，耗时约 1-2 分钟。

### 常用启动参数

```bash
# 自定义端口和绑定地址
python main.py --serve-only --host 0.0.0.0 --port 8888

# 指定股票并启动分析
python main.py --serve --stocks 600519,hk00700,AAPL

# 调试模式
python main.py --serve-only --debug
```

---

## 方式二：前后端分离开发

适合前端开发场景，支持热更新。

```bash
# 终端 1：启动后端 API（端口 8000）
python main.py --serve-only

# 终端 2：启动前端 Vite dev server（端口 5173）
cd apps/dsa-web
npm install
npm run dev
```

浏览器访问 **http://localhost:5173**，Vite 自动将 `/api` 请求代理到后端 `:8000`。

---

## 方式三：直接 uvicorn 启动

不经过 `main.py` 调度，仅启动 FastAPI 服务：

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

适用于仅需 API 服务或自行编排启动顺序的场景。

---

## 方式四：Docker 部署

```bash
# 完整服务（分析器 + API 服务）
docker-compose -f ./docker/docker-compose.yml up -d

# 仅 API 服务
docker-compose -f ./docker/docker-compose.yml up -d server
```

---

## 云服务器部署要点

### 1. 绑定外网地址

`.env` 中将 `WEBUI_HOST` 从默认的 `127.0.0.1` 改为 `0.0.0.0`：

```env
WEBUI_HOST=0.0.0.0
WEBUI_PORT=8000
```

### 2. 开放防火墙端口

```bash
# 以 ufw 为例
sudo ufw allow 8000/tcp
```

### 3. 启用登录认证（推荐）

```env
ADMIN_AUTH_ENABLED=true
# ADMIN_SESSION_MAX_AGE_HOURS=24
```

首次访问时在网页设置初始密码。忘记密码可执行：

```bash
python -m src.auth reset_password
```

### 4. Nginx 反向代理 + HTTPS（推荐生产环境）

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

配合 `.env`：

```env
TRUST_X_FORWARDED_FOR=true
```

---

## 关键 .env 配置项速查

### WebUI 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEBUI_ENABLED` | `false` | 使用 `--serve-only` 时无需改为 true |
| `WEBUI_HOST` | `127.0.0.1` | 云服务器改为 `0.0.0.0` |
| `WEBUI_PORT` | `8000` | 监听端口 |
| `WEBUI_AUTO_BUILD` | `true` | 启动时自动构建前端 |
| `ADMIN_AUTH_ENABLED` | `false` | 启用 Web 登录认证 |

### 分析配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STOCK_LIST` | `600519,300750,002594` | 自选股列表 |
| `REPORT_TYPE` | `simple` | `simple` / `full` / `brief` |
| `REPORT_LANGUAGE` | `zh` | `zh` / `en` |
| `SCHEDULE_ENABLED` | `false` | 定时任务开关 |
| `SCHEDULE_TIME` | `18:00` | 定时执行时间 |

### AI 模型（至少配一个）

| 变量 | 说明 |
|------|------|
| `GEMINI_API_KEY` | Google Gemini（有免费额度） |
| `DEEPSEEK_API_KEY` | DeepSeek（性价比高） |
| `ANTHROPIC_API_KEY` | Claude |
| `OPENAI_API_KEY` | OpenAI / 兼容 API |

---

## 架构示意

```
                 浏览器 http://localhost:8000
                           │
                 ┌─────────▼──────────┐
                 │   FastAPI (Uvicorn) │
                 │                    │
                 │  /api/v1/*  → API  │
                 │  /docs      → Swagger UI
                 │  /redoc     → ReDoc
                 │  /*         → 前端静态文件
                 └────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   数据源层           AI 分析层          搜索服务层
 (Tushare/AkShare   (LiteLLM →        (Tavily/Brave
  /Efinance/...)    Claude/Gemini/      /Anspire/...)
                    DeepSeek/...)
```

前端开发模式：

```
  浏览器 http://localhost:5173
           │
  ┌────────▼─────────┐
  │  Vite Dev Server  │ ← npm run dev
  │  (apps/dsa-web)   │
  │                   │
  │  /api/* ──proxy──▶│──▶ FastAPI :8000
  └───────────────────┘
```

---

## 故障排查

| 现象 | 原因 | 解决方案 |
|------|------|---------|
| 页面白屏 | 前端未构建 | `cd apps/dsa-web && npm ci && npm run build` |
| 云服务器无法访问 | 监听 localhost | `.env` 中 `WEBUI_HOST=0.0.0.0` |
| 端口被占用 | 其他进程占用 8000 | `--port 8888` 或改 `WEBUI_PORT` |
| 分析超时 | AI API Key 未配置 | 检查 `.env` 中的 API Key |
| 前端构建失败 | Node.js 版本过低 | 升级到 Node.js >= 18 |
| 忘记登录密码 | — | `python -m src.auth reset_password` |
