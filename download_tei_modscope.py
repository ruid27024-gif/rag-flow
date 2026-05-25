# from modelscope import snapshot_download

# # 更新为新的模型 ID
# model_id = 'vec-ai/lychee-embed'

# # 本地保存目录 (建议换个名字，避免和之前的模型混淆)
# cache_dir = './tei_data/vec-ai/lychee-embed' 

# print(f"正在下载模型 {model_id} ...")

# # 执行下载
# model_dir = snapshot_download(model_id, cache_dir=cache_dir)

# print(f"✅ 模型下载完成！")
# print(f"📂 本地路径: {model_dir}")

from modelscope import snapshot_download

# 修改为 BAAI 的 rerank 模型 ID
model_id = 'BAAI/bge-reranker-base'

# 本地保存目录
cache_dir = './tei_data/BAAI/bge-reranker-base'

print(f"正在下载模型 {model_id} ...")
model_dir = snapshot_download(model_id, cache_dir=cache_dir)
print(f"✅ 模型下载完成！路径: {model_dir}")