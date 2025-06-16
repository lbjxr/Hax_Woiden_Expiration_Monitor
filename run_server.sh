#!/bin/bash

set -e

echo "🧪 正在检查 Python3 环境..."

# 检查并安装 python3
if ! command -v python3 &>/dev/null; then
    echo "❌ 未检测到 python3，尝试自动安装..."
    if command -v apt &>/dev/null; then
        sudo apt update
        sudo apt install -y python3 python3-pip
    elif command -v yum &>/dev/null; then
        sudo yum install -y python3 python3-pip
    else
        echo "❌ 无法识别包管理器，退出。"
        exit 1
    fi
fi

# 检查并安装 pip3
if ! command -v pip3 &>/dev/null; then
    echo "❌ pip3 未安装，尝试自动安装..."
    if command -v apt &>/dev/null; then
        sudo apt install -y python3-pip
    elif command -v yum &>/dev/null; then
        sudo yum install -y python3-pip
    else
        echo "❌ 无法识别包管理器，退出。"
        exit 1
    fi
fi

# 获取 Python 主版本
PY_VER=$(python3 -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")

# 检查 venv 模块
echo "🔍 检查 venv 组件..."
if ! python3 -m venv --help &>/dev/null; then
    echo "⚠️ venv 不可用，自动安装 $PY_VER-venv、distutils、ensurepip..."
    sudo apt update
    sudo apt install -y ${PY_VER}-venv ${PY_VER}-distutils
    sudo python3 -m ensurepip --upgrade || true

fi

# 再次确认 venv 可用
if ! python3 -m venv --help &>/dev/null; then
    echo "❌ venv 模块仍不可用，Python 安装可能不完整。"
    exit 1
fi

echo "✅ Python3、pip3 和 venv 检查通过。"

# 创建虚拟环境
VENV_DIR=".venv"
mkdir -p logs

if [ ! -d "$VENV_DIR" ]; then
    echo "🛠 正在创建虚拟环境 $VENV_DIR..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo "⚠️ venv 创建失败，尝试修复依赖并重试..."
        sudo apt update
        sudo apt install -y ${PY_VER}-venv ${PY_VER}-distutils
        sudo python3 -m ensurepip --upgrade || true
        python3 -m venv "$VENV_DIR" || {
            echo "❌ 虚拟环境仍然创建失败，请手动检查。"
            exit 1
        }
    fi
fi

# 检查虚拟环境激活脚本
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "❌ 虚拟环境缺少 activate 脚本，创建失败。"
    exit 1
fi

# 激活虚拟环境
echo "🐍 正在激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 安装依赖
echo "📦 正在安装依赖（requirements.txt）..."
pip install --upgrade pip
pip install -r requirements.txt

# 启动选项
echo "🎯 请选择要启动的服务："
select choice in "后台运行 bot.py" "后台运行 hax.py" "全部后台运行" "退出"; do
    case $choice in
        "后台运行 bot.py")
            echo "🚀 正在后台启动 bot.py..."
            nohup "$VENV_DIR/bin/python" -u bot.py > logs/bot.log 2>&1 &
            echo "✅ bot.py 正在运行中，日志: logs/bot.log"
            break
            ;;
        "后台运行 hax.py")
            echo "🚀 正在后台启动 hax.py..."
            nohup "$VENV_DIR/bin/python" -u hax.py > logs/hax.log 2>&1 &
            echo "✅ hax.py 正在运行中，日志: logs/hax.log"
            break
            ;;
        "全部后台运行")
            echo "🚀 同时启动 bot.py 和 hax.py..."
            nohup "$VENV_DIR/bin/python" -u bot.py > logs/bot.log 2>&1 &
            nohup "$VENV_DIR/bin/python" -u hax.py > logs/hax.log 2>&1 &
            echo "✅ 两个程序均已运行，日志目录: logs/"
            break
            ;;
        "退出")
            echo "👋 已退出。"
            break
            ;;
        *)
            echo "⚠️ 请输入有效选项。"
            ;;
    esac
done
