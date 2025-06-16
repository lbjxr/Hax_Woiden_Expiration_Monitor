#!/bin/bash

set -e

# 构建 Docker 镜像
echo "🔧 正在构建 Docker 镜像..."
docker build -t my-bot-hax-app .

# 提示用户选择运行哪个服务
echo "请选择要运行的脚本："
select choice in "运行 bot.py" "运行 hax.py" "退出"; do
    case $choice in
        "运行 bot.py")
            echo "🚀 正在运行 Telegram Bot..."
            docker run -it --rm --name bot-app my-bot-hax-app python bot.py
            break
            ;;
        "运行 hax.py")
            echo "🚀 正在运行 HAX 监控脚本..."
            docker run -it --rm --name hax-app my-bot-hax-app python hax.py
            break
            ;;
        "退出")
            echo "已退出。"
            break
            ;;
        *)
            echo "❗ 无效选项，请重新选择。"
            ;;
    esac
done
