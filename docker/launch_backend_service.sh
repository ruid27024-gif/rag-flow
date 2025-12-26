#!/bin/bash

# 如果命令返回非零状态，立即退出脚本
set -e

# 从 .env 文件加载环境变量的函数
load_env_file() {
    # 获取当前脚本所在的目录
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local env_file="$script_dir/.env"

    # 检查 .env 文件是否存在
    if [ -f "$env_file" ]; then
        echo "正在从以下位置加载环境变量: $env_file"
        # 导出 .env 中的所有变量
        set -a
        source "$env_file" 
        set +a
    else
        echo "警告: 未在 $env_file 找到 .env 文件"
    fi
}

# 加载环境变量
load_env_file

# 清除可能由 Docker 守护进程设置的 HTTP 代理环境变量，防止干扰内部通信
export http_proxy=""; export https_proxy=""; export no_proxy=""; export HTTP_PROXY=""; export HTTPS_PROXY=""; export NO_PROXY=""
# 设置 Python 路径为当前目录
export PYTHONPATH=$(pwd)

# 设置共享库搜索路径
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/
# 获取 jemalloc 库的路径，用于优化内存分配
JEMALLOC_PATH=$(pkg-config --variable=libdir jemalloc)/libjemalloc.so

# 定义 Python 解释器
PY=python3

# 如果未设置 WS (Worker Size) 或其值小于 1，则默认设置为 1
if [[ -z "$WS" || $WS -lt 1 ]]; then
  WS=1
fi

# 每个任务执行器和服务器的最大重试次数
MAX_RETRIES=5

# 控制终止的标志位
STOP=false

# 记录所有子进程 PID 的数组
PIDS=()

# 设置 NLTK 数据目录路径
export NLTK_DATA="./nltk_data"

# 处理终止信号的清理函数
cleanup() {
  echo "接收到终止信号，正在关闭服务..."
  STOP=true
  # 终止所有记录在 PIDS 数组中的子进程
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      echo "正在停止进程 $pid"
      kill "$pid"
    fi
  done
  exit 0
}

# 捕获 SIGINT (Ctrl+C) 和 SIGTERM 信号并调用 cleanup 函数
trap cleanup SIGINT SIGTERM

# 执行任务执行器 (task_executor.py) 的函数，带有重试逻辑
task_exe(){
    local task_id=$1
    local retry_count=0
    while ! $STOP && [ $retry_count -lt $MAX_RETRIES ]; do
        echo "正在启动任务执行器 $task_id (尝试第 $((retry_count+1)) 次)"
        # 使用 jemalloc 预加载运行任务执行器
        LD_PRELOAD=$JEMALLOC_PATH $PY rag/svr/task_executor.py "$task_id" > debug-log/task_executor_"$task_id".log 2>&1 &
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 0 ]; then
            echo "任务执行器 $task_id 成功退出。"
            break
        else
            echo "任务执行器 $task_id 失败，退出码为 $EXIT_CODE。正在重试..." >&2
            retry_count=$((retry_count + 1))
            sleep 2
        fi
    done

    if [ $retry_count -ge $MAX_RETRIES ]; then
        echo "任务执行器 $task_id 在重试 $MAX_RETRIES 次后仍然失败。正在退出..." >&2
        cleanup
    fi
}

# 执行 RAGFlow API 服务 (ragflow_server.py) 的函数，带有重试逻辑
run_server(){
    local retry_count=0
    while ! $STOP && [ $retry_count -lt $MAX_RETRIES ]; do
        echo "正在启动 ragflow_server.py (尝试第 $((retry_count+1)) 次)"
        # 使用 jemalloc 预加载运行 API 服务
        LD_PRELOAD=$JEMALLOC_PATH $PY api/ragflow_server.py > debug-log/ragflow_server.log 2>&1 &
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 0 ]; then
            echo "ragflow_server.py 成功退出。"
            break
        else
            echo "ragflow_server.py 失败，退出码为 $EXIT_CODE。正在重试..." >&2
            retry_count=$((retry_count + 1))
            sleep 2
        fi
    done

    if [ $retry_count -ge $MAX_RETRIES ]; then
        echo "ragflow_server.py 在重试 $MAX_RETRIES 次后仍然失败。正在退出..." >&2
        cleanup
    fi
}

# 启动指定数量的任务执行器后台进程
for ((i=0;i<WS;i++))
do
  task_exe "$i" &
  PIDS+=($!)
done

# 启动 API 服务后台进程
run_server &
PIDS+=($!)

# 等待所有后台进程结束
wait
