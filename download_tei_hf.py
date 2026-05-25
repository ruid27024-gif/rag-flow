import os
from huggingface_hub import snapshot_download

# 设置镜像环境变量（必须在导入库之前或运行脚本前设置）
# 这里使用 os.environ 动态设置，无需在终端手动输入
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

model_id = 'Alibaba-NLP/gte-Qwen2-1.5B-instruct'
local_dir = './tei_data/Alibaba-NLP/gte-Qwen2-1.5B-instruct'

print(f"正在通过镜像站下载 {model_id} ...")

try:
    snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False, # 避免软链接问题，直接复制文件
        resume_download=True           # 开启断点续传
    )
    print("✅ 下载完成！")
except Exception as e:
    print(f"❌ 下载失败: {e}")