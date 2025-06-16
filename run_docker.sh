#!/bin/bash

set -e

# 构建 Docker 镜像（不需要把代码拷进镜像，镜像里只装环境依赖）
echo "🔧 正在构建 Docker 镜像..."
docker build -t my-bot-hax-app .

echo "请选择要运行的脚本："
select choice in "运行 bot.py" "运行 hax.py" "同时运行 bot.py 和 hax.py" "退出"; do
    case $choice in
        "运行 bot.py")
            echo "🚀 正在运行 Telegram Bot..."
            docker run -it --rm --name bot-app \
                -v "$(pwd):/app" \
                -w /app \
                my-bot-hax-app python bot.py
            break
            ;;
        "运行 hax.py")
            echo "🚀 正在运行 HAX 监控脚本..."
            docker run -it --rm --name hax-app \
                -v "$(pwd):/app" \
                -w /app \
                my-bot-hax-app python hax.py
            break
            ;;
        "同时运行 bot.py 和 hax.py")
            echo "🚀 同时启动 bot.py 和 hax.py 脚本..."

            docker rm -f bot-app hax-app 2>/dev/null || true

            docker run -d --name bot-app \
                -v "$(pwd):/app" \
                -w /app \
                my-bot-hax-app python bot.py

            docker run -d --name hax-app \
                -v "$(pwd):/app" \
                -w /app \
                my-bot-hax-app python hax.py

            echo "✅ 两个脚本均已启动（后台运行）"
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
