from modelscope import snapshot_download

# 模型 ID (ModelScope 上的 ID 通常和 HF 一样，或者是 Qwen/Qwen3-Embedding-0.6B)
model_id = 'Qwen/Qwen3-Embedding-0.6B'

# 本地保存目录
cache_dir = './tei_data' 

print(f"正在下载模型 {model_id} ...")

# 执行下载
# 注意：ModelScope 会自动将模型下载并整理到 cache_dir/Qwen/Qwen3-Embedding-0.6B 目录下
model_dir = snapshot_download(model_id, cache_dir=cache_dir)

print(f"✅ 模型下载完成！")
print(f"📂 本地路径: {model_dir}")