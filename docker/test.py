import requests

# 1. 配置你的 LocalAI 地址和模型名
url = "http://localhost:8080/v1/rerank"  # 注意这里是 /v1/rerank
headers = {
    "Content-Type": "application/json",
    # 如果你设置了 API Key，请在这里添加: "Authorization": "Bearer sk-..."
}

# 2. 构造请求体
# Rerank 模型的核心任务是：给“查询词”和“文档列表”的相关性打分
data = {
    "model": "Qwen3-Reranker-0.6B-q8_0.gguf", # 必须和你截图里的一模一样
    "query": "什么是量子力学？",               # 你的问题或搜索词
    "documents": [                            # 需要排序的文本段落列表
        "量子力学是物理学的一个分支，主要研究原子和亚原子尺度的物质。",
        "西红柿炒鸡蛋是一道经典的家常菜，做法简单。",
        "薛定谔方程是量子力学的核心方程，描述了量子态随时间的演化。",
        "今天天气真好，适合出去散步。"
    ],
    # 可选参数：
    # "top_n": 2,  # 如果只想返回相关性最高的前2个，可以加上这个
    # "return_documents": true # 如果希望返回结果里包含原文，设为 true
}

# 3. 发送请求
response = requests.post(url, headers=headers, json=data)

# 4. 查看结果
if response.status_code == 200:
    result = response.json()
    print("排序结果：")
    for rank in result['results']:
        index = rank['index']       # 原文档的索引
        score = rank['relevance_score'] # 相关性分数 (0-1之间，越接近1越相关)
        print(f"文档 {index}: 分数 {score:.4f} -> {data['documents'][index]}")
else:
    print(f"请求失败: {response.status_code}")
    print(response.text)