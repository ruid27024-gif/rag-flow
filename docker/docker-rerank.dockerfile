FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive

# 【新增步骤】将 Ubuntu 官方源替换为国内清华镜像源
# 这一步会把系统软件下载通道从国外切到国内，大幅提升 apt-get 的速度
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 安装基础依赖（现在会从清华源极速下载）
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip
RUN pip3 install --upgrade pip

# 安装 PyTorch 和 vLLM（pip 源你之前已经配置过国内镜像了，保持即可）
RUN pip3 install torch==2.3.0 torchvision torchaudio \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --find-links https://download.pytorch.org/whl/cu121

RUN pip3 install vllm==0.4.3

WORKDIR /app