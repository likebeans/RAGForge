#!/bin/bash
# Docker 容器启动脚本
# 启动 uvicorn 后自动进行健康检查预热

set -e

# 在后台启动 uvicorn
uv run uvicorn app.main:app --host 0.0.0.0 --port 8020 &
UVICORN_PID=$!

# 等待服务启动并进行预热
echo "等待服务启动..."
sleep 2

# 循环检查健康状态，最多等待 30 秒
for i in {1..30}; do
    if python3 -c "
import urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8020/health', timeout=2) as resp:
        if resp.status == 200:
            print('健康检查通过，服务已就绪')
            exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; then
        echo "✅ 服务预热完成"
        break
    fi
    echo "等待服务就绪... ($i/30)"
    sleep 1
done

# 将 uvicorn 进程放到前台
wait $UVICORN_PID
