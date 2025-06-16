# 使用官方 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制代码和依赖
COPY . /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 默认执行（可被 run.sh 覆盖）
CMD ["python", "bot.py"]
