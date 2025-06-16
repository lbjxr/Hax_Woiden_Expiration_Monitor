#!/bin/bash

set -e

echo "🧪 检查 Python3 环境..."

# 检查 python3 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到 python3，尝试自动安装..."

    # 判断包管理器
    if command -v apt &> /dev/null; then
        echo "🛠 使用 apt 安装 python3..."
        sudo apt update
        sudo apt install -y python3 python3-pip
    elif command -v yum &> /dev/null; then
        echo "🛠 使用 yum 安装 python3..."
        sudo yum install -y python3 python3-pip
    else
        echo "❌ 无法识别的包管理器，请手动安装 Python3 与 pip3。"
        exit 1
    fi
fi

# 检查 pip3
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 未安装，正在尝试安装..."
    if command -v apt &> /dev/null; then
        sudo apt install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    else
        echo "❌ 无法识别的包管理器，pip3 安装失败。"
        exit 1
    fi
fi

echo "✅ Python3 和 pip3 检查完成。"

# 创建 logs 目录
mkdir -p logs

# 安装依赖
echo "📦 安装 Python 依赖库..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# 用户选择运行哪个脚本
echo "请选择要启动的服务："
select choice in "后台运行 bot.py" "后台运行 hax.py" "全部后台运行" "退出"; do
    case $choice in
        "后台运行 bot.py")
            echo "🚀 正在后台启动 bot.py..."
            nohup python3 bot.py > logs/bot.log 2>&1 &
            echo "✅ bot.py 已在后台运行，日志: logs/bot.log"
            break
            ;;
        "后台运行 hax.py")
            echo "🚀 正在后台启动 hax.py..."
            nohup python3 hax.py > logs/hax.log 2>&1 &
            echo "✅ hax.py 已在后台运行，日志: logs/hax.log"
            break
            ;;
        "全部后台运行")
            echo "🚀 正在后台启动 bot.py 和 hax.py..."
            nohup python3 bot.py > logs/bot.log 2>&1 &
            nohup python3 hax.py > logs/hax.log 2>&1 &
            echo "✅ 两个程序均已运行，日志目录: logs/"
            break
            ;;
        "退出")
            echo "👋 已退出脚本。"
            break
            ;;
        *)
            echo "⚠️ 无效选项，请重新选择。"
            ;;
    esac
done
