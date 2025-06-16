# Telegram Bot + HAX 数据监控脚本

这是一个用于 Telegram Bot 管理和 HAX.CO.ID 数据中心监控的组合型项目，支持 **Docker 部署** 和 **服务器后台运行** 两种模式。

---

## 📦 功能简介

- 🤖 `bot.py`：一个使用 `python-telegram-bot` 实现的 Telegram Bot，支持交互式功能（如按钮、命令、回调）。
- 📡 `hax.py`：每 60 秒抓取 [https://hax.co.id/data-center/](https://hax.co.id/data-center/) 数据中心状态，。
- 🔁 支持后台自动运行（适配 Linux VPS）
- 🐳 提供 Docker 镜像构建脚本
- 📜 自动检查并安装 Python3 环境（服务器模式）

---

## 🖥️ 运行方式一：普通服务器后台运行

### ✅ 前提

- 适用于 Ubuntu / Debian / CentOS 等主流服务器
- Python 3 环境（可自动安装）

### ▶️ 一键运行

\`\`\`bash
chmod +x run_server.sh
./run_server.sh
\`\`\`

首次运行将：

- 检查系统是否安装 `python3` / `pip3`
- 自动安装 `requirements.txt` 依赖
- 启动你选择的脚本于后台（使用 `nohup`）
- 输出日志至 `logs/` 目录

### 📄 查看日志

\`\`\`bash
tail -f logs/bot.log     # 查看 Telegram Bot 日志
tail -f logs/hax.log     # 查看 HAX 监控日志
\`\`\`

### ❌ 停止进程

\`\`\`bash
pkill -f bot.py
pkill -f hax.py
\`\`\`

---

## 🐳 运行方式二：Docker 模式

### 🔧 构建镜像并运行

\`\`\`bash
chmod +x run.sh
./run.sh
\`\`\`

你可以选择运行：

- `bot.py`（Telegram Bot）
- `hax.py`（HAX 监控）
- 任意一个都可在容器中独立运行

---

## 📂 项目结构

\`\`\`
project/
├── bot.py               # Telegram Bot 主程序
├── hax.py               # HAX 数据中心监控脚本
├── requirements.txt     # 所有依赖声明
├── Dockerfile           # Docker 镜像定义
├── run.sh               # 一键 Docker 构建 + 启动脚本
├── run_server.sh        # 一键后台运行（非 Docker）
└── logs/                # 自动生成日志文件目录
\`\`\`

---

## 📌 依赖库

- `requests`
- `beautifulsoup4`
- `lxml`
- `python-telegram-bot >= 20.0`

安装方式：

\`\`\`bash
pip install -r requirements.txt
\`\`\`

---

## 📬 联系方式

欢迎 issue 或 PR，有建议请提！随缘回复
