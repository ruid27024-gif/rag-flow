# 使用 DaoCloud 镜像源（速度通常很快）
FROM docker.m.daocloud.io/nvidia/cuda:12.8.1-devel-ubuntu22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 配置 Ubuntu 清华镜像源
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 安装基础依赖（改用 Ubuntu 22.04 自带的 python3.10）
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    build-essential \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建符号链接 python3 -> python3.10
RUN ln -sf /usr/bin/python3.10 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.10 /usr/bin/python

# 升级 pip 并设置清华源（修正了你的链接语法）
RUN pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 PyTorch 使用清华源
RUN pip3 install torch==2.6.0 torchvision torchaudio \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 vLLM
RUN pip3 install vllm==0.6.2 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 设置工作目录
WORKDIR /app